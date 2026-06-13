import { Module } from '@nestjs/common';
import { SettingsModule } from '../settings/settings.module';
import { StatusModule } from '../status/status.module';
import { TelemetryModule } from '../telemetry/telemetry.module';
import { SimulatorService } from './simulator.service';

@Module({
  imports: [StatusModule, TelemetryModule, SettingsModule],
  providers: [SimulatorService],
})
export class SimulatorModule {}
