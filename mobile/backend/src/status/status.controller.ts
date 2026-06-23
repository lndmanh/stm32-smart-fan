import { Body, Controller, Get, Post, Put } from '@nestjs/common';
import {
  clampFanPercent,
  pwmToPercent,
  rpmToPercent,
} from '../device/fan-protocol';
import { SerialBridgeService } from '../device/serial-bridge.service';
import { SettingsService } from '../settings/settings.service';
import { SetControlModeDto } from './dto/set-control-mode.dto';
import { SetFanSpeedDto } from './dto/set-fan-speed.dto';
import { StatusService } from './status.service';

const ZERO_STATUS = {
  temperature: 0,
  fanSpeed: 0,
  pwm: 0,
  warning: 'Không có',
  rpm: 0,
  targetRpm: 0,
  faultCode: 0,
  state: null as string | null,
};

@Controller('status')
export class StatusController {
  constructor(
    private readonly statusService: StatusService,
    private readonly serialBridge: SerialBridgeService,
    private readonly settingsService: SettingsService,
  ) {}

  @Get()
  async getStatus() {
    const status = await this.statusService.getStatus();
    const sample = this.serialBridge.getLatestSample();
    const deviceConnected = this.serialBridge.isConnected();

    if (!sample) {
      return {
        ...ZERO_STATUS,
        controlMode: status.controlMode,
        dataSource: 'serial' as const,
        deviceConnected,
      };
    }

    const fanSpeed =
      status.controlMode === 'manual'
        ? rpmToPercent(sample.targetRpm)
        : rpmToPercent(sample.rpm);

    return {
      ...status,
      fanSpeed,
      pwm: pwmToPercent(sample.pwm),
      dataSource: 'serial' as const,
      deviceConnected,
      rpm: sample.rpm,
      targetRpm: sample.targetRpm,
      faultCode: sample.faultCode,
      state: sample.state,
    };
  }

  @Get('health')
  health() {
    return {
      ok: true,
      dataSource: 'serial',
      deviceConnected: this.serialBridge.isConnected(),
    };
  }

  @Post('reset-fault')
  async resetFault() {
    this.serialBridge.resetFaults();
    return this.getStatus();
  }

  @Put('fan')
  async setFanSpeed(@Body() dto: SetFanSpeedDto) {
    const settings = await this.settingsService.getOrCreateSettings();
    const fanSpeed = clampFanPercent(
      dto.fanSpeed,
      settings.fanMinSpeed,
      settings.fanMaxSpeed,
    );
    this.serialBridge.resetFaults();
    const status = await this.statusService.setFanSpeed(fanSpeed);
    this.serialBridge.setTargetPercent(fanSpeed);
    return status;
  }

  @Put('mode')
  async setControlMode(@Body() dto: SetControlModeDto) {
    const settings = await this.settingsService.getOrCreateSettings();
    const status = await this.statusService.setControlMode(dto.mode);
    const fanSpeed = clampFanPercent(
      status.fanSpeed,
      settings.fanMinSpeed,
      settings.fanMaxSpeed,
    );
    this.serialBridge.setControlMode(dto.mode, fanSpeed);
    if (fanSpeed !== status.fanSpeed) {
      return this.statusService.setFanSpeed(fanSpeed);
    }
    return status;
  }
}
