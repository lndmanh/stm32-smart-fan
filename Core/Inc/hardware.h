#ifndef HARDWARE_H
#define HARDWARE_H

#include <stdint.h>

void System_Init(void);
void Set_Motor_Output(int32_t u);
void UART2_Init(void);
int UART2_ReadChar(char *ch);
void UART2_WriteChar(char ch);
void UART2_WriteString(const char *text);

#endif /* HARDWARE_H */
