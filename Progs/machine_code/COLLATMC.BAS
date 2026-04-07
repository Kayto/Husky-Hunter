1 REM COLLATMC.HBA - Collatz: BASIC vs Machine Code
2 REM Runs same seed through both, prints step count and time
3 REM By kayto April 2026
4 REM For Husky Hunter (NSC800, 240x64 LCD)
5 REM
6 REM Z80 routine (33 bytes) at user code area F605H = 62981
7 REM Entry: E=seed high byte, C=seed low byte (from ARG)
8 REM Exit:  A=step count (returned via CALL)
9 REM Limit: seed intermediates must stay within 16-bit (65535)
10 REM        step count must be 255 or fewer
11 REM Safe test seeds: 27 (111 steps), 97 (118), 171 (124)
12 REM
20 KEY OFF:PRINT CHR$(1);"Collatz: BASIC vs MC"
22 PRINT "================================"
30 REM === Install Z80 Collatz routine ===
32 POKE 62981,99,105,6,0,124,183,32,5,125,254,1
34 POKE 62992,40,18,4,203,69,32,6,203,60,203,29
36 POKE 63003,24,236,229,41,209,25,35,24,229,120,201
38 DEFSEG=0
40 INPUT "Seed (0=quit) ";N
42 IF N=0 THEN KEY ON:END
44 IF N<2 THEN 40
46 PRINT CHR$(1);"Seed:";N
98 REM === Read RTC: tenths of seconds ===
99 REM F7E8=tenthsec F7E9=unitsec F7EA=tensec F7EB=unitmin F7EC=tenmin
100 REM === BASIC Collatz ===
102 GOSUB 900:T1=RT
104 BN=N:BS=0
110 IF BN=1 THEN 130
112 IF BN/2=INT(BN/2) THEN BN=BN/2:GOTO 120
114 BN=3*BN+1
120 BS=BS+1:GOTO 110
130 GOSUB 900:T2=RT
132 PRINT "BAS steps:";BS
134 BT=T2-T1:IF BT<0 THEN BT=BT+36000!
136 PRINT "BAS time :";BT/10;"s"
200 REM === Machine code Collatz ===
202 GOSUB 900:T1=RT
204 P=ARG(INT(N)):S=CALL(62981)
206 GOSUB 900:T2=RT
208 PRINT "MC  steps:";S
210 MT=T2-T1:IF MT<0 THEN MT=MT+36000!
212 PRINT "MC  time :";MT/10;"s"
220 IF BS=S THEN PRINT "MATCH" ELSE PRINT "MISMATCH!"
222 IF MT>0 THEN PRINT "Ratio: ";BT/MT;"x" ELSE PRINT "MC < 0.1s"
230 GOTO 40
900 REM === Read RTC to tenths of sec ===
902 P=ARG(48):X=CALL(5)
904 RT=PEEK(63464)+PEEK(63465)*10+PEEK(63466)*100
906 RT=RT+PEEK(63467)*1000+PEEK(63468)*10000
908 RETURN
