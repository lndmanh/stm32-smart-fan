import { forwardRef, Module } from '@nestjs/common';
import { SettingsModule } from '../settings/settings.module';
import { StatusModule } from '../status/status.module';
import { TelemetryModule } from '../telemetry/telemetry.module';
import { DeviceController } from './device.controller';
import { SerialBridgeService } from './serial-bridge.service';

@Module({
  imports: [
    forwardRef(() => StatusModule),
    TelemetryModule,
    SettingsModule,
  ],
  controllers: [DeviceController],
  providers: [SerialBridgeService],
  exports: [SerialBridgeService],
})
export class DeviceModule {}
