import { Body, Controller, Get, Put } from '@nestjs/common';
import { SerialBridgeService } from '../device/serial-bridge.service';
import { UpdatePidSettingsDto } from './dto/update-pid-settings.dto';
import { SettingsService } from './settings.service';

@Controller('settings')
export class SettingsController {
  constructor(
    private readonly settingsService: SettingsService,
    private readonly serialBridge: SerialBridgeService,
  ) {}

  @Get('pid')
  getPidSettings() {
    return this.settingsService.getPidSettings();
  }

  @Put('pid')
  async updatePidSettings(@Body() dto: UpdatePidSettingsDto) {
    const saved = await this.settingsService.updatePidSettings(dto);
    if (this.serialBridge.isActive()) {
      await this.serialBridge.applyPidSettings(dto.kp, dto.ki, dto.kd);
    }
    return saved;
  }
}
