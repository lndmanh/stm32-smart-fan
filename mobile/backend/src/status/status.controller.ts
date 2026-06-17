import { Body, Controller, Get, Put } from '@nestjs/common';
import { SerialBridgeService } from '../device/serial-bridge.service';
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

    return {
      ...status,
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

  @Put('fan')
  async setFanSpeed(@Body() dto: SetFanSpeedDto) {
    const status = await this.statusService.setFanSpeed(dto.fanSpeed);
    this.serialBridge.setTargetPercent(dto.fanSpeed);
    return status;
  }

  @Put('mode')
  async setControlMode(@Body() dto: SetControlModeDto) {
    const status = await this.statusService.setControlMode(dto.mode);
    this.serialBridge.setControlMode(dto.mode, status.fanSpeed);
    return status;
  }
}
