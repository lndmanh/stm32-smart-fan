import { forwardRef, Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { DeviceModule } from '../device/device.module';
import { SettingsModule } from '../settings/settings.module';
import { DeviceStatus } from './entities/device-status.entity';
import { StatusController } from './status.controller';
import { StatusService } from './status.service';

@Module({
  imports: [
    TypeOrmModule.forFeature([DeviceStatus]),
    forwardRef(() => DeviceModule),
    SettingsModule,
  ],
  controllers: [StatusController],
  providers: [StatusService],
  exports: [StatusService],
})
export class StatusModule {}
