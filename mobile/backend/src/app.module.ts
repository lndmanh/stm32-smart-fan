import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { DeviceModule } from './device/device.module';
import { SettingsModule } from './settings/settings.module';
import { StatusModule } from './status/status.module';
import { TelemetryModule } from './telemetry/telemetry.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    TypeOrmModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        type: 'postgres',
        host: config.get<string>('DATABASE_HOST', 'localhost'),
        port: parseInt(config.get<string>('DATABASE_PORT', '5433'), 10),
        username: config.get<string>('DATABASE_USER', 'postgres'),
        password: config.get<string>('DATABASE_PASSWORD', 'postgres'),
        database: config.get<string>('DATABASE_NAME', 'fan'),
        autoLoadEntities: true,
        synchronize: true,
      }),
    }),
    DeviceModule,
    StatusModule,
    TelemetryModule,
    SettingsModule,
  ],
})
export class AppModule {}
