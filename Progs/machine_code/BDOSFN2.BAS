10 REM BDOS fn2 demo - console output via ARG and CALL
20 REM Demonstrates the Hunter BASIC machine code interface:
30 REM   ARG   - D=ARG(N) loads Z80 E (high byte) and C (low byte)
40 REM   CALL  - D=CALL(N) executes at address N, returns A register
50 REM
60 REM No Z80 stub or POKE needed - ARG+CALL(5) invokes BDOS directly
70 REM BDOS fn2 (console output): C=02H (fn), E=character ASCII value
80 REM ARG(E*256 + C) = ARG(char*256 + 2) loads both registers at once
90 REM For 4100: E=16, C=4 since 16*256+4=4100 (manual 5.2.2)
100 REM
110 DEFSEG=0
120 REM
130 REM Send "HELLO FROM BDOS" one character at a time
140 MS$="HELLO FROM BDOS"
150 FOR K=1 TO LEN(MS$)
160   CH=ASC(MID$(MS$,K,1))
170   P=ARG(CH*256+2)
180   X=CALL(5)
190 NEXT K
200 REM Send CR+LF to finish line
210 P=ARG(13*256+2):X=CALL(5)
220 P=ARG(10*256+2):X=CALL(5)
230 END
