// Minimal platform shim so the controller core builds on AVR and on a PC.
#pragma once
#include <stdint.h>

#if defined(__AVR__)
#include <avr/interrupt.h>
#include <avr/io.h>
#define SF_ATOMIC_BEGIN { uint8_t sf_sreg_ = SREG; cli();
#define SF_ATOMIC_END   SREG = sf_sreg_; }
#else
#define SF_ATOMIC_BEGIN {
#define SF_ATOMIC_END   }
#endif

// Flash-resident string literals on AVR (RAM is 2 KB on the Uno).
#if defined(__AVR__)
#include <avr/pgmspace.h>
#define SF_P(s) PSTR(s)
#define sf_strcpy_P strcpy_P
#define sf_strcat_P strcat_P
#define sf_strncpy_P strncpy_P
#else
#include <string.h>
#define SF_P(s) (s)
#define sf_strcpy_P strcpy
#define sf_strcat_P strcat
#define sf_strncpy_P strncpy
#endif

#if defined(__AVR__)
#include <stdio.h>
#define SF_SNPRINTF(buf, n, fmt, ...) snprintf_P(buf, n, PSTR(fmt), __VA_ARGS__)
#else
#include <stdio.h>
#define SF_SNPRINTF(buf, n, fmt, ...) snprintf(buf, n, fmt, __VA_ARGS__)
#endif
