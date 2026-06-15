import { Body, Controller, Get, Put } from '@nestjs/common';
import { SerialBridgeService } from '../device/serial-bridge.service';
import { SetControlModeDto } from './dto/set-control-mode.dto';
import { SetFanSpeedDto } from './dto/set-fan-speed.dto';
import { StatusService } from './status.service';

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

    return {
      ...status,
      dataSource: this.serialBridge.isActive() ? 'serial' : 'simulator',
      deviceConnected: this.serialBridge.isConnected(),
      rpm: sample?.rpm ?? null,
      targetRpm: sample?.targetRpm ?? null,
      faultCode: sample?.faultCode ?? null,
      state: sample?.state ?? null,
    };
  }

  @Get('health')
  health() {
    return {
      ok: true,
      dataSource: this.serialBridge.isActive() ? 'serial' : 'simulator',
      deviceConnected: this.serialBridge.isConnected(),
    };
  }

  @Put('fan')
  async setFanSpeed(@Body() dto: SetFanSpeedDto) {
    const status = await this.statusService.setFanSpeed(dto.fanSpeed);
    if (this.serialBridge.isActive()) {
      await this.serialBridge.setTargetPercent(dto.fanSpeed);
    }
    return status;
  }

  @Put('mode')
  async setControlMode(@Body() dto: SetControlModeDto) {
    const status = await this.statusService.setControlMode(dto.mode);
    if (this.serialBridge.isActive() && dto.mode === 'manual') {
      await this.serialBridge.setTargetPercent(status.fanSpeed);
    }
    return status;
  }
}
