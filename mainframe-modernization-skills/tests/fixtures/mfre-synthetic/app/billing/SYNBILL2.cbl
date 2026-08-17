      *****************************************************************
      * SYNBILL2 - SYNTHETIC FIXTURE PROGRAM. NOT REAL SOURCE.        *
      * Invoice totalling for the invoice cycle.                      *
      *****************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SYNBILL2.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-INVOICE-TOTAL        PIC S9(9)V99 COMP-3 VALUE ZERO.
       01  WS-CREDIT-ADJUST        PIC S9(7)V99 COMP-3 VALUE ZERO.
       01  WS-EVENT-NET            PIC S9(9)V99 COMP-3 VALUE ZERO.
       COPY SYNACCT.
       PROCEDURE DIVISION.
       0000-MAIN.
           PERFORM 3000-ACCUMULATE
           PERFORM 4000-APPLY-ADJUSTMENT
           GOBACK.
       3000-ACCUMULATE.
           ADD WS-EVENT-NET TO WS-INVOICE-TOTAL
              ON SIZE ERROR
                 DISPLAY 'SYNBILL2: INVOICE TOTAL OVERFLOW'
                 MOVE 12 TO RETURN-CODE
                 GOBACK
           END-ADD.
       4000-APPLY-ADJUSTMENT.
           IF WS-CREDIT-ADJUST NOT = ZERO
              SUBTRACT WS-CREDIT-ADJUST FROM WS-INVOICE-TOTAL
                 ON SIZE ERROR
                    DISPLAY 'SYNBILL2: ADJUSTMENT UNDERFLOW'
              END-SUBTRACT
           END-IF.
