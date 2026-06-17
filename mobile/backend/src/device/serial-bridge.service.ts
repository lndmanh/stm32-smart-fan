import {
  Injectable,
  Logger,
  OnModuleDestroy,
  OnModuleInit,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { SerialPort } from 'serialport';
import { ReadlineParser } from '@serialport/parser-readline';
import { SettingsService } from '../settings/settings.service';
import { StatusService } from '../status/status.service';
import { TelemetryService } from '../telemetry/telemetry.service';
import {
  FanTelemetrySample,
  buildAutoModeCommand,
  buildManualModeCommand,
  buildPidCommand,
  buildResetFaultsCommand,
  buildSetSpeedCommand,
  buildStopCommand,
  parseFanTelemetryLine,
  percentToRpm,
  pwmToPercent,
  rpmToPercent,
} from './fan-protocol';

@Injectable()
export class SerialBridgeService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(SerialBridgeService.name);
  private port: SerialPort | null = null;
  private parser: ReadlineParser | null = null;
  private latest: FanTelemetrySample | null = null;
  private connected = false;

  constructor(
    private readonly config: ConfigService,
    private readonly statusService: StatusService,
    private readonly telemetryService: TelemetryService,
    private readonly settingsService: SettingsService,
  ) {}

  onModuleInit() {
    if (!this.isSerialMode()) {
      this.logger.log('Serial bridge disabled (simulator mode)');
      return;
    }

    const portPath = this.config.get<string>('SERIAL_PORT', '').trim();
    if (!portPath) {
      this.logger.warn('DEVICE_MODE=serial but SERIAL_PORT is empty');
      return;
    }

    this.connect(portPath);
  }

  onModuleDestroy() {
    this.disconnect();
  }

  isSerialMode(): boolean {
    return this.config.get<string>('DEVICE_MODE', 'simulator') === 'serial';
  }

  isActive(): boolean {
    return this.isSerialMode();
  }

  getLatestSample(): FanTelemetrySample | null {
    return this.latest;
  }

  isConnected(): boolean {
    return this.connected;
  }

  async listPorts(): Promise<string[]> {
    const ports = await SerialPort.list();
    return ports.map((port) => port.path);
  }

  sendRaw(command: string): void {
    if (!this.port?.isOpen) {
      throw new Error('STM32 serial port is not connected');
    }
    this.port.write(command);
  }

  async setTargetPercent(percent: number): Promise<void> {
    this.sendRaw(buildSetSpeedCommand(percentToRpm(percent)));
  }

  async applyPidSettings(kp: number, ki: number, kd: number): Promise<void> {
    this.sendRaw(buildPidCommand('kp', kp));
    this.sendRaw(buildPidCommand('ki', ki));
    this.sendRaw(buildPidCommand('kd', kd));
  }

  async stopFan(): Promise<void> {
    this.sendRaw(buildStopCommand());
  }

  async resetFaults(): Promise<void> {
    this.sendRaw(buildResetFaultsCommand());
  }

  async setControlMode(mode: 'auto' | 'manual', fanSpeed?: number): Promise<void> {
    if (mode === 'auto') {
      this.sendRaw(buildAutoModeCommand());
      return;
    }

    this.sendRaw(buildManualModeCommand());
    if (fanSpeed != null) {
      this.sendRaw(buildSetSpeedCommand(percentToRpm(fanSpeed)));
    }
  }

  private connect(portPath: string) {
    const baudRate = parseInt(
      this.config.get<string>('SERIAL_BAUD', '115200'),
      10,
    );

    this.port = new SerialPort({
      path: portPath,
      baudRate,
      autoOpen: false,
    });

    this.parser = this.port.pipe(new ReadlineParser({ delimiter: '\n' }));
    this.parser.on('data', (line: string) => {
      void this.handleLine(line);
    });

    this.port.on('open', () => {
      this.connected = true;
      this.logger.log(`Connected to STM32 on ${portPath} @ ${baudRate}`);
    });

    this.port.on('close', () => {
      this.connected = false;
      this.logger.warn(`Serial port ${portPath} closed`);
    });

    this.port.on('error', (error) => {
      this.connected = false;
      this.logger.error(`Serial error on ${portPath}`, error);
    });

    this.port.open((error) => {
      if (error) {
        this.logger.error(`Failed to open ${portPath}`, error);
      }
    });
  }

  private disconnect() {
    this.parser?.removeAllListeners();
    this.parser = null;

    if (this.port?.isOpen) {
      this.port.close();
    }
    this.port = null;
    this.connected = false;
  }

  private async handleLine(line: string) {
    const sample = parseFanTelemetryLine(line);
    if (!sample) {
      return;
    }

    this.latest = sample;
    const settings = await this.settingsService.getOrCreateSettings();
    const fanSpeed = rpmToPercent(sample.rpm);
    const pwm = pwmToPercent(sample.pwm);

    let warning = 'Không có';
    if (sample.temperatureC >= Number(settings.temperatureThreshold) + 5) {
      warning = 'Nhiệt độ vượt ngưỡng an toàn';
    } else if (sample.temperatureC >= Number(settings.temperatureThreshold)) {
      warning = 'Nhiệt độ cao';
    }
    if (sample.faultCode !== 0) {
      warning = `Fault ${sample.faultCode} (${sample.state})`;
    }

    await this.statusService.updateStatus({
      temperature: sample.temperatureC,
      fanSpeed,
      pwm,
      warning,
    });

    await this.telemetryService.addReading('temperature', sample.temperatureC);
    await this.telemetryService.addReading('fanSpeed', fanSpeed);
    await this.telemetryService.addReading('pwm', pwm);
  }
}
