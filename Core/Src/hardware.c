#include "hardware.h"
#include "stm32f401xe.h"

#define SYS_CLOCK       16000000U
#define PWM_FREQ        10000U
#define PWM_ARR         ((SYS_CLOCK / PWM_FREQ) - 1U)

#define UART_BAUD_RATE 115200U

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
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN | RCC_APB1ENR_TIM3EN | RCC_APB1ENR_USART2EN;

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
    USART2->CR1 = 0U;
    USART2->CR2 = 0U;
    USART2->CR3 = 0U;
    USART2->BRR = (SYS_CLOCK + (UART_BAUD_RATE / 2U)) / UART_BAUD_RATE;
    USART2->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
}

int UART2_ReadChar(char *ch) {
    if ((USART2->SR & USART_SR_RXNE) == 0U) {
        return 0;
    }

    *ch = (char)(USART2->DR & 0xFFU);
    return 1;
}

void UART2_WriteChar(char ch) {
    while ((USART2->SR & USART_SR_TXE) == 0U) {
    }

    USART2->DR = (uint32_t)(uint8_t)ch;
}

void UART2_WriteString(const char *text) {
    while (*text != '\0') {
        UART2_WriteChar(*text++);
    }
}
