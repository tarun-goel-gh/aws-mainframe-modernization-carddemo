      *****************************************************************
      * SYNPAY1 - SYNTHETIC FIXTURE PROGRAM. NOT REAL SOURCE.         *
      * Online payment capture and balance update.                    *
      *****************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SYNPAY1.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-RESP                 PIC S9(08) COMP.
       01  WS-RESP2                PIC S9(08) COMP.
       01  WS-PAY-AMOUNT           PIC S9(9)V99 COMP-3 VALUE ZERO.
       01  WS-MESSAGE              PIC X(79) VALUE SPACES.
       COPY SYNACCT.
       PROCEDURE DIVISION.
       0000-MAIN.
           PERFORM 1000-VALIDATE
           PERFORM 2000-POST-PAYMENT
           EXEC CICS RETURN END-EXEC.
       1000-VALIDATE.
           IF WS-PAY-AMOUNT NOT NUMERIC OR WS-PAY-AMOUNT <= ZERO
              MOVE 'PAYMENT AMOUNT INVALID' TO WS-MESSAGE
              PERFORM 8000-SEND-MESSAGE
           END-IF.
       2000-POST-PAYMENT.
           EXEC CICS READ
                FILE('SYNBAL')
                INTO(SYN-ACCT-RECORD)
                RIDFLD(SYN-ACCT-ID)
                UPDATE
                RESP(WS-RESP)
                RESP2(WS-RESP2)
           END-EXEC
           EVALUATE WS-RESP
              WHEN DFHRESP(NORMAL)
                 SUBTRACT WS-PAY-AMOUNT FROM SYN-ACCT-BALANCE
                 EXEC CICS REWRITE FILE('SYNBAL')
                      FROM(SYN-ACCT-RECORD)
                      RESP(WS-RESP)
                 END-EXEC
              WHEN DFHRESP(NOTFND)
                 MOVE 'ACCOUNT NOT FOUND' TO WS-MESSAGE
                 PERFORM 8000-SEND-MESSAGE
              WHEN DFHRESP(LOCKED)
                 MOVE 'RECORD HELD, TRY AGAIN' TO WS-MESSAGE
                 PERFORM 8000-SEND-MESSAGE
              WHEN OTHER
                 MOVE 'UNEXPECTED FILE CONDITION' TO WS-MESSAGE
                 PERFORM 8000-SEND-MESSAGE
           END-EVALUATE.
       8000-SEND-MESSAGE.
           EXEC CICS SEND TEXT
                FROM(WS-MESSAGE)
                ERASE
                RESP(WS-RESP)
           END-EXEC.
