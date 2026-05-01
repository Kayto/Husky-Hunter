1 REM SND1 - Four Octave Scale Demo
2 REM Plays all 29 notes low-to-high then high-to-low
3 REM Then continuous pitch sweeps up and down
4 REM ESC to exit at any time  By kayto April 2026
5 KEY OFF:SCREEN 0:PRINT CHR$(1);
10 CHAR 1
12 PRINT "SND1: SCALE DEMO"
14 PRINT "================"
16 PRINT "29 notes, 4 octaves"
18 PRINT "(ESC to quit)"
20 PRINT
30 REM Note pitches from Appendix 9.13 (low to high freq)
32 REM Higher pitch# = lower frequency (inverse scale)
34 DIM NP(28)
36 FOR I=0 TO 28:READ NP(I):NEXT I
40 DATA 493,439,391,368,326,290,260
41 DATA 244,217,193,182,162,144,128
42 DATA 121,107,95,90,80,71,63
43 DATA 59,52,46,43,38,34,30,28
50 REM --- Scale: ascending frequency ---
52 PRINT "Ascending scale..."
54 FOR I=0 TO 28
56 A$=INKEY$:IF A$=CHR$(27) THEN GOTO 900
58 SOUND NP(I),200
60 NEXT I
70 REM --- Scale: descending frequency ---
72 PRINT "Descending scale..."
74 FOR I=28 TO 0 STEP -1
76 A$=INKEY$:IF A$=CHR$(27) THEN GOTO 900
78 SOUND NP(I),200
80 NEXT I
90 REM --- Continuous sweep: ascending frequency ---
92 PRINT "Sweep: ascending..."
94 FOR I=490 TO 30 STEP -15
96 A$=INKEY$:IF A$=CHR$(27) THEN GOTO 900
98 SOUND I,25
100 NEXT I
110 REM --- Continuous sweep: descending frequency ---
112 PRINT "Sweep: descending..."
114 FOR I=30 TO 490 STEP 15
116 A$=INKEY$:IF A$=CHR$(27) THEN GOTO 900
118 SOUND I,25
120 NEXT I
130 PRINT "Done - any key"
132 A$=INKEY$:IF A$="" THEN 132
900 SCREEN 0:PRINT CHR$(1);:CURON:END
