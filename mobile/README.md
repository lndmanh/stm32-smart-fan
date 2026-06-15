# Hệ thống giám sát & điều khiển quạt

Bài tập lớn môn **Cơ sở đo lường và điều khiển số**.

App mobile xem nhiệt độ, tốc độ quạt, PWM. Backend xử lý dữ liệu và mô phỏng cảm biến (chưa nối phần cứng thật).

## Công nghệ

| Phần | Stack |
|------|-------|
| Mobile | React Native + Expo (`mobile/`) |
| Backend | NestJS + Fastify (`backend/`) |
| Database | PostgreSQL (`infra/`) |

## Chức năng chính

- Xem **nhiệt độ**, **tốc độ quạt**, **PWM** realtime + đồ thị
- **Tự động**: nhiệt cao → quạt quay nhanh hơn (PID)
- **Thủ công**: tự chỉnh tốc độ quạt trên app
- Cảnh báo khi nhiệt vượt ngưỡng
- Cài đặt tham số PID / ngưỡng nhiệt độ

## Giao diện

### Màn hình giám sát

![Trang chủ - nhiệt độ & quạt](docs/screenshots/home-1.png)

![Trang chủ - PWM & cảnh báo](docs/screenshots/home-2.png)

### Điều khiển quạt

Chế độ tự động theo nhiệt độ:

![Điều khiển quạt - tự động](docs/screenshots/fan-auto.png)

Chế độ thủ công, chỉnh bằng nút +/- hoặc preset:

![Điều khiển quạt - thủ công](docs/screenshots/fan-manual.png)

### Cài đặt PID

![Cài đặt PID](docs/screenshots/pid-settings.png)

## Cấu trúc project

```
mobile/
├── mobile/      # app Expo
├── backend/     # API NestJS
├── infra/       # Docker Postgres
└── docs/        # ảnh demo
```

## Chạy project

`cd` vào thư mục `mobile/` trước.

### 1. Database

```bash
cd infra
cp .env.example .env
docker compose up -d
```

### 2. Backend

```bash
cd backend
cp .env.example .env
npm install
npm run start:dev
```

API chạy tại `http://localhost:3000`

### 3. Mobile

```bash
cd mobile
cp .env.example .env
```

Sửa `EXPO_PUBLIC_API_URL` trong `.env`:
- Máy thật (Expo Go): `http://<IP-máy-tính>:3000`
- Android emulator: `http://10.0.2.2:3000`

```bash
npm install
npx expo start
```

Quét QR bằng Expo Go, điện thoại và máy tính cùng WiFi.

## API (tóm tắt)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/status` | Trạng thái hiện tại |
| PUT | `/api/status/fan` | Đặt tốc độ quạt |
| PUT | `/api/status/mode` | `auto` / `manual` |
| GET | `/api/telemetry/temperature` | Lịch sử nhiệt độ |
| GET | `/api/telemetry/fan-speed` | Lịch sử tốc độ quạt |
| GET | `/api/telemetry/pwm` | Lịch sử PWM |
| GET/PUT | `/api/settings/pid` | Cài đặt PID |

## Lưu ý

- Postgres Docker dùng port **5433** (tránh trùng Postgres cài sẵn trên máy)
- Dữ liệu cảm biến đang **mô phỏng** trên backend, cập nhật mỗi 3 giây
- Cần backend chạy trước khi mở app mobile
