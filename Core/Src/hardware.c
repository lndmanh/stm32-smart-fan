#include "hardware.h"
#include "stm32f401xe.h"

#define SYS_CLOCK       16000000U
#define PWM_FREQ        10000U
#define PWM_ARR         ((SYS_CLOCK / PWM_FREQ) - 1U)

#define UART_BAUD_RATE 115200U

// Thêm 3 biến này để làm cái "kho" chứa dữ liệu
volatile char rx_buffer[64];
volatile uint8_t rx_head = 0;
volatile uint8_t rx_tail = 0;

// Hàm ngắt: Tự động được gọi mỗi khi có 1 ký tự gửi từ máy tính xuống
void USART1_IRQHandler(void) {
    if (USART1->SR & USART_SR_RXNE) {
        char ch = (char)(USART1->DR & 0xFFU);
        rx_buffer[rx_head] = ch;
        rx_head = (rx_head + 1U) % 64U; // Vòng lặp lại nếu đầy
    }
}

void Set_Motor_Output(int32_t u) {
    if (u >= 0) {
        GPIOA->ODR |= (1U << 9);
        GPIOA->ODR &= ~(1U << 10);
        TIM1->CCR1 = (uint32_t)u;
    } else {
        GPIOA->ODR &= ~(1U << 9);
        GPIOA->ODR |= (1U << 10);
        TIM1->CCR1 = (uint32_t)(-u);
    }
}

void System_Init(void) {
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOBEN;
    RCC->APB2ENR |= RCC_APB2ENR_TIM1EN;

    // Tắt USART2 ở APB1, bật clock cho USART1 ở APB2
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN | RCC_APB1ENR_TIM3EN;
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;

    // ========================================================
    // 🔥 CẤU HÌNH ĐÁNH THỨC MẠCH CẦU H TB6612 (PB10)
    // ========================================================
    GPIOB->MODER &= ~(3U << (10U * 2U)); // Xóa cấu hình cũ của chân PB10
    GPIOB->MODER |=  (1U << (10U * 2U)); // Cấu hình PB10 làm chân OUTPUT (Ngõ ra)
    GPIOB->ODR   |=  (1U << 10);         // Kéo chân PB10 lên mức HIGH để bật STBY

    // ========================================================
    // 🔥 CẤU HÌNH CHÂN PB6 (TX) VÀ PB7 (RX) CHO USART1
    // ========================================================
    GPIOB->MODER &= ~((3U << (6U * 2U)) | (3U << (7U * 2U))); // Xóa cấu hình GPIO cũ PB6, PB7
    GPIOB->MODER |=  ((2U << (6U * 2U)) | (2U << (7U * 2U))); // Đặt thành Alternate Function (AF)

    GPIOB->AFR[0] &= ~((15U << (6U * 4U)) | (15U << (7U * 4U))); // Xóa cấu hình AF cũ
    GPIOB->AFR[0] |=  ((7U << (6U * 4U))  | (7U << (7U * 4U)));  // Đặt Alternate Function 7 (AF7) cho USART1
    // ========================================================

    GPIOA->MODER &= ~(
        (3U << (0U * 2U)) |
        (3U << (1U * 2U)) |
        (3U << (2U * 2U)) |
        (3U << (3U * 2U)) |
        (3U << (8U * 2U)) |
        (3U << (9U * 2U)) |
        (3U << (10U * 2U))
    );
    GPIOA->MODER |=
        (2U << (0U * 2U)) |
        (2U << (1U * 2U)) |
        (2U << (2U * 2U)) |
        (2U << (3U * 2U)) |
        (2U << (8U * 2U)) |
        (1U << (9U * 2U)) |
        (1U << (10U * 2U));

    GPIOA->AFR[0] &= ~((15U << 0) | (15U << 4) | (15U << 8) | (15U << 12));
    GPIOA->AFR[0] |= (1U << 0) | (1U << 4) | (7U << 8) | (7U << 12);

    GPIOA->AFR[1] &= ~(15U << 0);
    GPIOA->AFR[1] |= (1U << 0);

    TIM1->PSC = 0U;
    TIM1->ARR = PWM_ARR;
    TIM1->CCR1 = 0U;
    TIM1->CCMR1 |= (6U << 4) | TIM_CCMR1_OC1PE;
    TIM1->CCER |= TIM_CCER_CC1E;
    TIM1->BDTR |= TIM_BDTR_MOE;
    TIM1->CR1 |= TIM_CR1_CEN;

    TIM2->CCMR1 |= (1U << 0) | (1U << 8);
    TIM2->SMCR |= (3U << 0);
    TIM2->CR1 |= TIM_CR1_CEN;

    TIM3->PSC = 15999U;
    TIM3->ARR = 9U;
    TIM3->DIER |= TIM_DIER_UIE;
    NVIC_EnableIRQ(TIM3_IRQn);
TIM3->CR1 |= TIM_CR1_CEN;

    UART2_Init();
}

void UART2_Init(void) {
    USART1->CR1 = 0U;
    USART1->CR2 = 0U;
    USART1->CR3 = 0U;
    USART1->BRR = (SYS_CLOCK + (UART_BAUD_RATE / 2U)) / UART_BAUD_RATE;

    // 🔥 Bật thêm ngắt nhận dữ liệu (RXNEIE)
    USART1->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE | USART_CR1_RXNEIE;
    NVIC_EnableIRQ(USART1_IRQn);
}

int UART2_ReadChar(char *ch) {
    if (rx_head == rx_tail) {
        return 0; // Kho rỗng, chưa có dữ liệu mới
    }

    // Có dữ liệu thì lấy ra từ kho
    *ch = rx_buffer[rx_tail];
    rx_tail = (rx_tail + 1U) % 64U;
    return 1;
}

void UART2_WriteChar(char ch) {
    while ((USART1->SR & USART_SR_TXE) == 0U) {
    }

    USART1->DR = (uint32_t)(uint8_t)ch;
}

void UART2_WriteString(const char *text) {
    while (*text != '\0') {
        UART2_WriteChar(*text++);
    }
}
