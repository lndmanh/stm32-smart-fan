import { Injectable, Logger } from '@nestjs/common';
import { Interval } from '@nestjs/schedule';
import { SerialBridgeService } from '../device/serial-bridge.service';
import { SettingsService } from '../settings/settings.service';
import { StatusService } from '../status/status.service';
import { TelemetryService } from '../telemetry/telemetry.service';

@Injectable()
export class SimulatorService {
  private readonly logger = new Logger(SimulatorService.name);
  private integral = 0;
  private previousError = 0;

  constructor(
    private readonly statusService: StatusService,
    private readonly telemetryService: TelemetryService,
    private readonly settingsService: SettingsService,
    private readonly serialBridge: SerialBridgeService,
  ) {}

  @Interval(3000)
  async simulateReading() {
    if (this.serialBridge.isActive()) {
      return;
    }

    try {
      const current = await this.statusService.getStatus();
      const settings = await this.settingsService.getOrCreateSettings();

      const noise = (Math.random() - 0.5) * 0.8;
      const drift =
        current.temperature >= Number(settings.temperatureThreshold)
          ? 0.35
          : -0.12;
      const temperature =
        Math.round((current.temperature + drift + noise) * 10) / 10;

      let fanSpeed = current.fanSpeed;
      let pwm = current.pwm;

      if (current.controlMode === 'auto') {
        const error = temperature - Number(settings.temperatureThreshold);
        this.integral += error;
        const derivative = error - this.previousError;
        this.previousError = error;

        const pidOutput =
          Number(settings.kp) * error +
          Number(settings.ki) * this.integral * 0.01 +
          Number(settings.kd) * derivative;

        const tempRatio = this.clamp(
          (temperature - 55) / (Number(settings.temperatureThreshold) - 55),
          0,
          1,
        );
        const tempBasedSpeed = Math.round(
          settings.fanMinSpeed +
            tempRatio * (settings.fanMaxSpeed - settings.fanMinSpeed),
        );

        pwm = this.clamp(
          Math.round(tempBasedSpeed * 0.6 + (50 + pidOutput * 4) * 0.4),
          settings.fanMinSpeed,
          settings.fanMaxSpeed,
        );
        fanSpeed = this.clamp(
          Math.round(pwm * 0.97 + Math.random() * 2),
          settings.fanMinSpeed,
          settings.fanMaxSpeed,
        );
      }

      let warning = 'Không có';
      if (temperature >= Number(settings.temperatureThreshold) + 5) {
        warning = 'Nhiệt độ vượt ngưỡng an toàn';
      } else if (temperature >= Number(settings.temperatureThreshold)) {
        warning = 'Nhiệt độ cao';
      }

      await this.statusService.updateStatus({
        temperature,
        fanSpeed,
        pwm,
        warning,
      });

      await this.telemetryService.addReading('temperature', temperature);
      await this.telemetryService.addReading('fanSpeed', fanSpeed);
      await this.telemetryService.addReading('pwm', pwm);
    } catch (error) {
      this.logger.warn('Simulator tick failed', error);
    }
  }

  private clamp(value: number, min: number, max: number) {
    return Math.min(max, Math.max(min, value));
  }
}
