import { Body, Controller, Get, Put } from '@nestjs/common';
import { SetControlModeDto } from './dto/set-control-mode.dto';
import { SetFanSpeedDto } from './dto/set-fan-speed.dto';
import { StatusService } from './status.service';

@Controller('status')
export class StatusController {
  constructor(private readonly statusService: StatusService) {}

  @Get()
  getStatus() {
    return this.statusService.getStatus();
  }

  @Get('health')
  health() {
    return { ok: true };
  }

  @Put('fan')
  setFanSpeed(@Body() dto: SetFanSpeedDto) {
    return this.statusService.setFanSpeed(dto.fanSpeed);
  }

  @Put('mode')
  setControlMode(@Body() dto: SetControlModeDto) {
    return this.statusService.setControlMode(dto.mode);
  }
}
