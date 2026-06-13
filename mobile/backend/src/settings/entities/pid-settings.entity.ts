import { Column, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity('pid_settings')
export class PidSettings {
  @PrimaryGeneratedColumn()
  id: number;

  @Column('decimal', { precision: 6, scale: 3, default: 1.0 })
  kp: number;

  @Column('decimal', { precision: 6, scale: 3, default: 0.1 })
  ki: number;

  @Column('decimal', { precision: 6, scale: 3, default: 0.05 })
  kd: number;

  @Column('decimal', { precision: 5, scale: 1, default: 80.0 })
  temperatureThreshold: number;

  @Column('int', { default: 20 })
  fanMinSpeed: number;

  @Column('int', { default: 100 })
  fanMaxSpeed: number;
}
