import {
  Column,
  CreateDateColumn,
  Entity,
  PrimaryGeneratedColumn,
} from 'typeorm';

export type TelemetryMetric = 'temperature' | 'fanSpeed' | 'pwm';

@Entity('telemetry_readings')
export class TelemetryReading {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ length: 20, default: 'temperature' })
  metric: TelemetryMetric;

  @Column('decimal', { precision: 5, scale: 1 })
  value: number;

  @CreateDateColumn()
  createdAt: Date;
}
