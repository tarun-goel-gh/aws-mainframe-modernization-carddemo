      *****************************************************************
      * SYNACCT - SYNTHETIC FIXTURE COPYBOOK. NOT REAL SOURCE.        *
      *****************************************************************
       01  SYN-ACCT-RECORD.
           05  SYN-ACCT-ID          PIC X(11).
           05  SYN-ACCT-STATUS      PIC X(01).
               88  ACCT-ACTIVE                VALUE 'A'.
               88  ACCT-DORMANT               VALUE 'D'.
           05  SYN-ACCT-BALANCE     PIC S9(10)V99 COMP-3.
           05  SYN-ACCT-CYCLE-FLAG  PIC X(01).
               88  ACCT-CYCLE-OPEN            VALUE 'Y'.
           05  FILLER               PIC X(43).
