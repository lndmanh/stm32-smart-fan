import { Injectable, OnModuleInit } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import {
  TelemetryMetric,
  TelemetryReading,
} from './entities/telemetry-reading.entity';

const SEED_TEMP = [72, 74, 76, 78, 77, 79, 78, 80, 79, 78];
const SEED_FAN = [30, 35, 42, 50, 48, 55, 58, 62, 60, 62];
const SEED_PWM = [28, 33, 40, 48, 46, 53, 56, 60, 58, 62];

@Injectable()
export class TelemetryService implements OnModuleInit {
  constructor(
    @InjectRepository(TelemetryReading)
    private readonly readingRepo: Repository<TelemetryReading>,
  ) {}

  async onModuleInit() {
    const count = await this.readingRepo.count();
    if (count === 0) {
      await this.readingRepo.save([
        ...SEED_TEMP.map((value) =>
          this.readingRepo.create({ metric: 'temperature', value }),
        ),
        ...SEED_FAN.map((value) =>
          this.readingRepo.create({ metric: 'fanSpeed', value }),
        ),
        ...SEED_PWM.map((value) =>
          this.readingRepo.create({ metric: 'pwm', value }),
        ),
      ]);
    }
  }

  async getHistory(
    metric: TelemetryMetric,
    limit = 20,
  ): Promise<{ points: number[] }> {
    const readings = await this.readingRepo.find({
      where: { metric },
      order: { createdAt: 'DESC' },
      take: limit,
    });

    return {
      points: readings.reverse().map((r) => Number(r.value)),
    };
  }

  async addReading(metric: TelemetryMetric, value: number): Promise<void> {
    await this.readingRepo.save(
      this.readingRepo.create({ metric, value }),
    );
    await this.trimOldReadings(metric, 50);
  }

  private async trimOldReadings(metric: TelemetryMetric, maxCount: number) {
    const count = await this.readingRepo.count({ where: { metric } });
    if (count <= maxCount) return;

    const excess = count - maxCount;
    const oldest = await this.readingRepo.find({
      where: { metric },
      order: { createdAt: 'ASC' },
      take: excess,
    });
    await this.readingRepo.remove(oldest);
  }
}
