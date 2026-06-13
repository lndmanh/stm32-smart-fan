import { Type } from 'class-transformer';
import { IsInt, IsNumber, Max, Min } from 'class-validator';

export class UpdatePidSettingsDto {
  @Type(() => Number)
  @IsNumber()
  @Min(0)
  kp: number;

  @Type(() => Number)
  @IsNumber()
  @Min(0)
  ki: number;

  @Type(() => Number)
  @IsNumber()
  @Min(0)
  kd: number;

  @Type(() => Number)
  @IsNumber()
  @Min(0)
  @Max(200)
  temperatureThreshold: number;

  @Type(() => Number)
  @IsInt()
  @Min(0)
  @Max(100)
  fanMinSpeed: number;

  @Type(() => Number)
  @IsInt()
  @Min(0)
  @Max(100)
  fanMaxSpeed: number;
}
