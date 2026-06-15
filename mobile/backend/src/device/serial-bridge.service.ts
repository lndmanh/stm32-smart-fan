import {
  Injectable,
  Logger,
  OnModuleDestroy,
  OnModuleInit,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Interval } from '@nestjs/schedule';
import { SerialPort } from 'serialport';
import { ReadlineParser } from '@serialport/parser-readline';
import { SettingsService } from '../settings/settings.service';
import { StatusService } from '../status/status.service';
import { TelemetryService } from '../telemetry/telemetry.service';
import {
  FanTelemetrySample,
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
  private autoIntegral = 0;
  private autoPreviousError = 0;

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

  @Interval(3000)
  async autoControlTick() {
    if (!this.isActive()) {
      return;
    }

    try {
      const status = await this.statusService.getStatus();
      if (status.controlMode !== 'auto') {
        return;
      }

      const settings = await this.settingsService.getOrCreateSettings();
      const temperature = status.temperature;
      const error = temperature - Number(settings.temperatureThreshold);
      this.autoIntegral += error;
      const derivative = error - this.autoPreviousError;
      this.autoPreviousError = error;

      const pidOutput =
        Number(settings.kp) * error +
        Number(settings.ki) * this.autoIntegral * 0.01 +
        Number(settings.kd) * derivative;

      const tempRatio = this.clamp(
        (temperature - 55) / (Number(settings.temperatureThreshold) - 55),
        0,
        1,
      );
      const tempBasedPercent = Math.round(
        settings.fanMinSpeed +
          tempRatio * (settings.fanMaxSpeed - settings.fanMinSpeed),
      );
      const targetPercent = this.clamp(
        Math.round(tempBasedPercent * 0.6 + (50 + pidOutput * 4) * 0.4),
        settings.fanMinSpeed,
        settings.fanMaxSpeed,
      );

      this.sendRaw(buildSetSpeedCommand(percentToRpm(targetPercent)));
    } catch (error) {
      this.logger.warn('Auto control tick failed', error);
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

  private clamp(value: number, min: number, max: number) {
    return Math.min(max, Math.max(min, value));
  }
}
