import {
  Column,
  Entity,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';

@Entity('device_status')
export class DeviceStatus {
  @PrimaryGeneratedColumn()
  id: number;

  @Column('decimal', { precision: 5, scale: 1, default: 78.3 })
  temperature: number;

  @Column('int', { default: 62 })
  fanSpeed: number;

  @Column('int', { default: 65 })
  pwm: number;

  @Column({ default: 'Không có' })
  warning: string;

  @Column({ default: 'auto' })
  controlMode: 'auto' | 'manual';

  @UpdateDateColumn()
  updatedAt: Date;
}
