import { Controller, Get, Query } from '@nestjs/common';
import { TelemetryMetric } from './entities/telemetry-reading.entity';
import { TelemetryService } from './telemetry.service';

@Controller('telemetry')
export class TelemetryController {
  constructor(private readonly telemetryService: TelemetryService) {}

  @Get('temperature')
  getTemperatureHistory(@Query('limit') limit?: string) {
    return this.getHistory('temperature', limit);
  }

  @Get('fan-speed')
  getFanSpeedHistory(@Query('limit') limit?: string) {
    return this.getHistory('fanSpeed', limit);
  }

  @Get('pwm')
  getPwmHistory(@Query('limit') limit?: string) {
    return this.getHistory('pwm', limit);
  }

  private getHistory(metric: TelemetryMetric, limit?: string) {
    const parsed = limit ? parseInt(limit, 10) : 20;
    return this.telemetryService.getHistory(
      metric,
      Number.isNaN(parsed) ? 20 : parsed,
    );
  }
}
