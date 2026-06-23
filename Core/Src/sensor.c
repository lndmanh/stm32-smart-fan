/******************************************************************************
 * sensor.c
 *
 * Temperature acquisition and filtering module.
 ******************************************************************************/
#include "sensor.h"
#include "main.h"

// Đã chuyển sang chân PB0
#define DS18B20_PORT GPIOB
#define DS18B20_PIN  GPIO_PIN_0

#define FILTER_SIZE 10
#define SENSOR_ERROR_VALUE -1000.0f

static float temp_buffer[FILTER_SIZE] = {0};
static uint8_t buffer_index = 0;
static uint8_t sample_count = 0;

/* Microsecond delay using DWT */
static void delay_us(uint32_t us)
{
    uint32_t start = DWT->CYCCNT;
    uint32_t ticks = us * (HAL_RCC_GetHCLKFreq() / 1000000);
    while ((DWT->CYCCNT - start) < ticks);
}

/* Initialize DWT timer and Configure PB0 as Open-Drain ONCE */
void Sensor_Init(void)
{
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    // Cấu hình chân MỘT LẦN DUY NHẤT ở chế độ Open-Drain
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = DS18B20_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_OD;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(DS18B20_PORT, &GPIO_InitStruct);

    // Nhả chân lên mức HIGH
    HAL_GPIO_WritePin(DS18B20_PORT, DS18B20_PIN, GPIO_PIN_SET);
}

/* Send reset pulse and check presence pulse */
static uint8_t DS18B20_Reset(void)
{
    uint8_t presence = 0;

    HAL_GPIO_WritePin(DS18B20_PORT, DS18B20_PIN, GPIO_PIN_RESET);
    delay_us(480);

    HAL_GPIO_WritePin(DS18B20_PORT, DS18B20_PIN, GPIO_PIN_SET);
    delay_us(80);

    if (HAL_GPIO_ReadPin(DS18B20_PORT, DS18B20_PIN) == GPIO_PIN_RESET)
    {
        presence = 1;
    }

    delay_us(400);
    return presence;
}

/* Write one bit to DS18B20 */
static void DS18B20_WriteBit(uint8_t bit)
{
    __disable_irq(); // Khóa ngắt
    HAL_GPIO_WritePin(DS18B20_PORT, DS18B20_PIN, GPIO_PIN_RESET);

    if (bit)
    {
        delay_us(2);
        HAL_GPIO_WritePin(DS18B20_PORT, DS18B20_PIN, GPIO_PIN_SET);
        delay_us(60);
    }
    else
    {
        delay_us(60);
        HAL_GPIO_WritePin(DS18B20_PORT, DS18B20_PIN, GPIO_PIN_SET);
        delay_us(2);
    }
    __enable_irq(); // Mở ngắt
}

/* Read one bit from DS18B20 */
static uint8_t DS18B20_ReadBit(void)
{
    uint8_t bit = 0;

    __disable_irq(); // Khóa ngắt
    HAL_GPIO_WritePin(DS18B20_PORT, DS18B20_PIN, GPIO_PIN_RESET);
    delay_us(2);

    HAL_GPIO_WritePin(DS18B20_PORT, DS18B20_PIN, GPIO_PIN_SET);
    delay_us(10);

    if (HAL_GPIO_ReadPin(DS18B20_PORT, DS18B20_PIN) == GPIO_PIN_SET)
    {
        bit = 1;
    }
    __enable_irq(); // Mở ngắt

    delay_us(50);
    return bit;
}

/* Write one byte to DS18B20 */
static void DS18B20_WriteByte(uint8_t data)
{
    for (uint8_t i = 0; i < 8; i++)
    {
        DS18B20_WriteBit(data & 0x01);
        data >>= 1;
    }
}

/* Read one byte from DS18B20 */
static uint8_t DS18B20_ReadByte(void)
{
    uint8_t data = 0;

    for (uint8_t i = 0; i < 8; i++)
    {
        data >>= 1;

        if (DS18B20_ReadBit())
        {
            data |= 0x80;
        }
    }
    return data;
}

/* Read raw temperature from DS18B20 */
static float DS18B20_ReadRawTemperature(void)
{
    uint8_t temp_lsb;
    uint8_t temp_msb;
    int16_t raw_temp;
    float temperature;

    if (!DS18B20_Reset())
    {
        return SENSOR_ERROR_VALUE;
    }

    DS18B20_WriteByte(0xCC);   // Skip ROM
    DS18B20_WriteByte(0x44);   // Convert T

    HAL_Delay(750);

    if (!DS18B20_Reset())
    {
        return SENSOR_ERROR_VALUE;
    }

    DS18B20_WriteByte(0xCC);   // Skip ROM
    DS18B20_WriteByte(0xBE);   // Read Scratchpad

    temp_lsb = DS18B20_ReadByte();
    temp_msb = DS18B20_ReadByte();

    raw_temp = (int16_t)((temp_msb << 8) | temp_lsb);
    temperature = raw_temp / 16.0f;

    return temperature;
}

/* Moving average filter */
static float MovingAverageFilter(float new_sample)
{
    float sum = 0.0f;

    temp_buffer[buffer_index] = new_sample;
    buffer_index++;

    if (buffer_index >= FILTER_SIZE)
    {
        buffer_index = 0;
    }

    if (sample_count < FILTER_SIZE)
    {
        sample_count++;
    }

    for (uint8_t i = 0; i < sample_count; i++)
    {
        sum += temp_buffer[i];
    }

    return sum / sample_count;
}

/* Read filtered temperature */
float Sensor_ReadTemperature(void)
{
    float raw_temperature;

    raw_temperature = DS18B20_ReadRawTemperature();

    if (raw_temperature == SENSOR_ERROR_VALUE)
    {
        return SENSOR_ERROR_VALUE;
    }

    return MovingAverageFilter(raw_temperature);
}
