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

  async onModuleInit() {
    if (!this.isSerialMode()) {
      this.logger.log('Serial bridge disabled (simulator mode)');
      return;
    }

    await this.statusService.resetToZeros();
    await this.telemetryService.clearAll();

    const portPath = await this.resolvePortPath();
    if (!portPath) {
      this.logger.warn(
        'No serial port configured or detected — waiting for STM32 (values default to 0)',
      );
      return;
    }

    this.connect(portPath);
  }

  onModuleDestroy() {
    this.disconnect();
  }

  isSerialMode(): boolean {
    return this.config.get<string>('DEVICE_MODE', 'serial') === 'serial';
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

  sendRaw(command: string): boolean {
    if (!this.port?.isOpen) {
      this.logger.warn(`Serial not open, skip: ${command.trim()}`);
      return false;
    }
    this.port.write(command);
    return true;
  }

  setTargetPercent(percent: number): void {
    this.sendRaw(buildSetSpeedCommand(percentToRpm(percent)));
  }

  applyPidSettings(kp: number, ki: number, kd: number): void {
    this.sendRaw(buildPidCommand('kp', kp));
    this.sendRaw(buildPidCommand('ki', ki));
    this.sendRaw(buildPidCommand('kd', kd));
  }

  stopFan(): void {
    this.sendRaw(buildStopCommand());
  }

  resetFaults(): void {
    this.sendRaw(buildResetFaultsCommand());
  }

  setControlMode(mode: 'auto' | 'manual', fanSpeed?: number): void {
    if (mode === 'auto') {
      this.sendRaw(buildAutoModeCommand());
      return;
    }

    this.sendRaw(buildManualModeCommand());
    if (fanSpeed != null) {
      this.sendRaw(buildSetSpeedCommand(percentToRpm(fanSpeed)));
    }
  }

  private async resolvePortPath(): Promise<string | null> {
    const configured = this.config.get<string>('SERIAL_PORT', '').trim();
    if (configured) {
      return configured;
    }

    const ports = await this.listPorts();
    if (ports.length === 0) {
      return null;
    }

    const autoPort = ports[0];
    this.logger.log(`SERIAL_PORT not set — auto-selected ${autoPort}`);
    return autoPort;
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
      void this.clearDeviceReading();
      this.logger.warn(`Serial port ${portPath} closed`);
    });

    this.port.on('error', (error) => {
      this.connected = false;
      void this.clearDeviceReading();
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
    this.latest = null;
  }

  private async clearDeviceReading() {
    this.latest = null;
    await this.statusService.resetToZeros();
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
