import { BadRequestException, Injectable, OnModuleInit } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { UpdatePidSettingsDto } from './dto/update-pid-settings.dto';
import { PidSettings } from './entities/pid-settings.entity';

@Injectable()
export class SettingsService implements OnModuleInit {
  constructor(
    @InjectRepository(PidSettings)
    private readonly settingsRepo: Repository<PidSettings>,
  ) {}

  async onModuleInit() {
    const count = await this.settingsRepo.count();
    if (count === 0) {
      await this.settingsRepo.save(
        this.settingsRepo.create({
          kp: 1.0,
          ki: 0.1,
          kd: 0.05,
          temperatureThreshold: 80.0,
          fanMinSpeed: 20,
          fanMaxSpeed: 100,
        }),
      );
    }
  }

  async getPidSettings() {
    const settings = await this.getOrCreate();
    return this.toResponse(settings);
  }

  async updatePidSettings(dto: UpdatePidSettingsDto) {
    if (dto.fanMinSpeed > dto.fanMaxSpeed) {
      throw new BadRequestException('fanMinSpeed must be <= fanMaxSpeed');
    }

    const settings = await this.getOrCreate();
    Object.assign(settings, dto);
    const saved = await this.settingsRepo.save(settings);
    return this.toResponse(saved);
  }

  async getOrCreateSettings(): Promise<PidSettings> {
    return this.getOrCreate();
  }

  private async getOrCreate(): Promise<PidSettings> {
    let settings = await this.settingsRepo.findOne({ where: { id: 1 } });
    if (!settings) {
      settings = await this.settingsRepo.save(
        this.settingsRepo.create({
          kp: 1.0,
          ki: 0.1,
          kd: 0.05,
          temperatureThreshold: 80.0,
          fanMinSpeed: 20,
          fanMaxSpeed: 100,
        }),
      );
    }
    return settings;
  }

  private toResponse(settings: PidSettings) {
    return {
      kp: Number(settings.kp),
      ki: Number(settings.ki),
      kd: Number(settings.kd),
      temperatureThreshold: Number(settings.temperatureThreshold),
      fanMinSpeed: settings.fanMinSpeed,
      fanMaxSpeed: settings.fanMaxSpeed,
    };
  }
}
