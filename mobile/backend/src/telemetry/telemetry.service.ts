import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import {
  TelemetryMetric,
  TelemetryReading,
} from './entities/telemetry-reading.entity';

@Injectable()
export class TelemetryService {
  constructor(
    @InjectRepository(TelemetryReading)
    private readonly readingRepo: Repository<TelemetryReading>,
  ) {}

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

  async clearAll(): Promise<void> {
    await this.readingRepo.clear();
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
