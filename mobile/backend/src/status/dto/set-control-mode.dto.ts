import { IsIn } from 'class-validator';

export class SetControlModeDto {
  @IsIn(['auto', 'manual'])
  mode: 'auto' | 'manual';
}
