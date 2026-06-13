import { Body, Controller, Get, Put } from '@nestjs/common';
import { UpdatePidSettingsDto } from './dto/update-pid-settings.dto';
import { SettingsService } from './settings.service';

@Controller('settings')
export class SettingsController {
  constructor(private readonly settingsService: SettingsService) {}

  @Get('pid')
  getPidSettings() {
    return this.settingsService.getPidSettings();
  }

  @Put('pid')
  updatePidSettings(@Body() dto: UpdatePidSettingsDto) {
    return this.settingsService.updatePidSettings(dto);
  }
}
