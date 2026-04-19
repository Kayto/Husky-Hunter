1 REM ELTA.BAS v1.0 - Zeiss Elta Reader
2 REM Receives data from Elta total station
3 REM By kayto 19/04/2026
4 REM For Husky Hunter (NSC800, 240x64 LCD)
10 KEY OFF:PRINT CHR$(1);
12 PRINT "Zeiss Elta Reader"
14 PRINT
20 REM --- SETUP SERIAL ---
22 POKE 63480,6:POKE 63481,6   :REM TX/RX baud = 1200
24 POKE 63487,1:POKE 63488,1   :REM TX/RX parity = Odd (7-bit)
26 POKE 63482,0                 :REM CTS = No
28 POKE 63493,0                 :REM RX protocol = None
30 PRINT "Awaiting Elta data..."
32 PRINT "ESC after line to quit"
34 PRINT
100 REM === MAIN LOOP ===
102 LINPUT "",A$
104 IF A$="" THEN GOTO 100
106 PRINT A$
108 K$=INKEY$:IF K$=CHR$(27) THEN GOTO 200
110 GOTO 100
200 REM === EXIT ===
202 KEY ON
204 PRINT :PRINT "Done."
206 END
