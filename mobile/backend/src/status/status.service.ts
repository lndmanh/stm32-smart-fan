import { Injectable, OnModuleInit } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { DeviceStatus } from './entities/device-status.entity';

export type StatusResponse = {
  temperature: number;
  fanSpeed: number;
  pwm: number;
  warning: string;
  controlMode: 'auto' | 'manual';
};

@Injectable()
export class StatusService implements OnModuleInit {
  constructor(
    @InjectRepository(DeviceStatus)
    private readonly statusRepo: Repository<DeviceStatus>,
  ) {}

  async onModuleInit() {
    const count = await this.statusRepo.count();
    if (count === 0) {
      await this.saveDefaults();
    }
  }

  async resetToZeros(): Promise<StatusResponse> {
    return this.updateStatus({
      temperature: 0,
      fanSpeed: 0,
      pwm: 0,
      warning: 'Không có',
    });
  }

  async getStatus(): Promise<StatusResponse> {
    const status = await this.getOrCreate();
    return this.toResponse(status);
  }

  async updateStatus(data: Partial<StatusResponse>): Promise<StatusResponse> {
    const status = await this.getOrCreate();
    Object.assign(status, data);
    const saved = await this.statusRepo.save(status);
    return this.toResponse(saved);
  }

  async setFanSpeed(fanSpeed: number): Promise<StatusResponse> {
    const clamped = Math.min(100, Math.max(0, Math.round(fanSpeed)));
    return this.updateStatus({
      fanSpeed: clamped,
      pwm: clamped,
      controlMode: 'manual',
    });
  }

  async setControlMode(mode: 'auto' | 'manual'): Promise<StatusResponse> {
    return this.updateStatus({ controlMode: mode });
  }

  private async getOrCreate(): Promise<DeviceStatus> {
    let status = await this.statusRepo.findOne({ where: { id: 1 } });
    if (!status) {
      status = await this.saveDefaults();
    }
    return status;
  }

  private async saveDefaults(): Promise<DeviceStatus> {
    return this.statusRepo.save(
      this.statusRepo.create({
        temperature: 0,
        fanSpeed: 0,
        pwm: 0,
        warning: 'Không có',
        controlMode: 'auto',
      }),
    );
  }

  private toResponse(status: DeviceStatus): StatusResponse {
    return {
      temperature: Number(status.temperature),
      fanSpeed: status.fanSpeed,
      pwm: status.pwm,
      warning: status.warning,
      controlMode: status.controlMode ?? 'auto',
    };
  }
}
