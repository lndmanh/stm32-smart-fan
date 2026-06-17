import { Controller, Get } from '@nestjs/common';
import { SerialBridgeService } from './serial-bridge.service';

@Controller('device')
export class DeviceController {
  constructor(private readonly serialBridge: SerialBridgeService) {}

  @Get('ports')
  listPorts() {
    return this.serialBridge.listPorts();
  }

  @Get('connection')
  connection() {
    return {
      mode: 'serial',
      connected: this.serialBridge.isConnected(),
      sample: this.serialBridge.getLatestSample(),
    };
  }
}
