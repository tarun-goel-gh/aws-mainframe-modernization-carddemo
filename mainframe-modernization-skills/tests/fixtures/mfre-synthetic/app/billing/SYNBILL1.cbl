      *****************************************************************
      * SYNBILL1 - SYNTHETIC FIXTURE PROGRAM. NOT REAL SOURCE.        *
      * Billing event selection for the invoice cycle.                *
      *****************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SYNBILL1.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT SYN-BEVT-FILE ASSIGN TO SYNBEVT
                  ORGANIZATION IS INDEXED
                  ACCESS MODE  IS SEQUENTIAL
                  RECORD KEY   IS SYN-BEVT-KEY
                  FILE STATUS  IS WS-BEVT-STATUS.
       DATA DIVISION.
       FILE SECTION.
       FD  SYN-BEVT-FILE.
       01  SYN-BEVT-RECORD.
           05  SYN-BEVT-KEY        PIC X(11).
           05  SYN-BEVT-POSTED     PIC X(01).
           05  SYN-BEVT-NET        PIC S9(9)V99 COMP-3.
       WORKING-STORAGE SECTION.
       01  WS-BEVT-STATUS          PIC X(02).
       01  WS-SELECTED-COUNT       PIC 9(07) VALUE ZERO.
       01  WS-CYCLE-OPEN-FLAG      PIC X(01) VALUE 'N'.
           88  CYCLE-IS-OPEN                 VALUE 'Y'.
       COPY SYNACCT.
       PROCEDURE DIVISION.
       0000-MAIN.
           PERFORM 1000-OPEN-FILES
           PERFORM 2000-SELECT-EVENTS
           PERFORM 9000-CLOSE-FILES
           GOBACK.
       1000-OPEN-FILES.
           OPEN INPUT SYN-BEVT-FILE
           IF WS-BEVT-STATUS NOT = '00'
              DISPLAY 'SYNBILL1: OPEN FAILED ' WS-BEVT-STATUS
              MOVE 16 TO RETURN-CODE
              GOBACK
           END-IF.
       2000-SELECT-EVENTS.
           IF NOT CYCLE-IS-OPEN
              DISPLAY 'SYNBILL1: CYCLE CLOSED, NO SELECTION'
              GO TO 2000-EXIT
           END-IF
           PERFORM UNTIL WS-BEVT-STATUS = '10'
              READ SYN-BEVT-FILE
                 AT END
                    MOVE '10' TO WS-BEVT-STATUS
                 NOT AT END
                    PERFORM 2100-EVALUATE-EVENT
              END-READ
           END-PERFORM.
       2000-EXIT.
           EXIT.
       2100-EVALUATE-EVENT.
           EVALUATE SYN-BEVT-POSTED
              WHEN 'Y'
                 ADD 1 TO WS-SELECTED-COUNT
              WHEN 'N'
                 CONTINUE
              WHEN OTHER
                 DISPLAY 'SYNBILL1: EXCEPTION ' SYN-BEVT-KEY
           END-EVALUATE.
       9000-CLOSE-FILES.
           CLOSE SYN-BEVT-FILE.
