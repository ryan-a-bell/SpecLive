# Transcript → requirements: eval report

| case | provider | strategy | recall | wtd-recall | precision | F1 | type-acc | has-ev | correct-turn | grounded |
|------|----------|----------|--------|-----------|-----------|----|----------|--------|--------------|----------|
| hospital-bed-mgmt | mock | segment |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| hospital-bed-mgmt | mock | window |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| hospital-bed-mgmt | mock | full |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| hpc-infrastructure | mock | segment |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| hpc-infrastructure | mock | window |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| hpc-infrastructure | mock | full |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| iot-warehouse-ml | mock | segment |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| iot-warehouse-ml | mock | window |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| iot-warehouse-ml | mock | full |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| speclive-itself | mock | segment |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| speclive-itself | mock | window |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| speclive-itself | mock | full |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| warehouse-modernization | mock | segment |   27% |   30% |   60% |   38% |  100% |  100% |  100% |  100% |
| warehouse-modernization | mock | window |   27% |   30% |   60% |   38% |  100% |  100% |  100% |  100% |
| warehouse-modernization | mock | full |   27% |   30% |   60% |   38% |  100% |  100% |  100% |  100% |

_matcher: LexicalMatcher, threshold 0.3_


## Per-run detail

### hospital-bed-mgmt · mock · segment (threshold 0.3)

- counts: 0/16 gold recovered, 6 derived, 6 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.693
- missed gold: C1, C2, C3, C4, M1, M2, M3, N1, N2, O1, Q1, Q2, R1, R2, R3, R4

### hospital-bed-mgmt · mock · window (threshold 0.3)

- counts: 0/16 gold recovered, 6 derived, 6 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.693
- missed gold: C1, C2, C3, C4, M1, M2, M3, N1, N2, O1, Q1, Q2, R1, R2, R3, R4

### hospital-bed-mgmt · mock · full (threshold 0.3)

- counts: 0/16 gold recovered, 6 derived, 6 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.693
- missed gold: C1, C2, C3, C4, M1, M2, M3, N1, N2, O1, Q1, Q2, R1, R2, R3, R4

### hpc-infrastructure · mock · segment (threshold 0.3)

- counts: 0/10 gold recovered, 2 derived, 2 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.655
- missed gold: C1, C2, C3, D1, O1, R1, R2, R3, R4, RISK1

### hpc-infrastructure · mock · window (threshold 0.3)

- counts: 0/10 gold recovered, 2 derived, 2 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.655
- missed gold: C1, C2, C3, D1, O1, R1, R2, R3, R4, RISK1

### hpc-infrastructure · mock · full (threshold 0.3)

- counts: 0/10 gold recovered, 2 derived, 2 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.655
- missed gold: C1, C2, C3, D1, O1, R1, R2, R3, R4, RISK1

### iot-warehouse-ml · mock · segment (threshold 0.3)

- counts: 0/13 gold recovered, 4 derived, 4 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.632
- missed gold: A1, C1, C2, C3, M1, O1, Q1, R1, R2, R3, R4, R5, R6

### iot-warehouse-ml · mock · window (threshold 0.3)

- counts: 0/13 gold recovered, 4 derived, 4 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.632
- missed gold: A1, C1, C2, C3, M1, O1, Q1, R1, R2, R3, R4, R5, R6

### iot-warehouse-ml · mock · full (threshold 0.3)

- counts: 0/13 gold recovered, 4 derived, 4 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.632
- missed gold: A1, C1, C2, C3, M1, O1, Q1, R1, R2, R3, R4, R5, R6

### speclive-itself · mock · segment (threshold 0.3)

- counts: 0/12 gold recovered, 3 derived, 3 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.647
- missed gold: C1, C2, C3, N1, N2, O1, R1, R2, R3, R4, R5, R7

### speclive-itself · mock · window (threshold 0.3)

- counts: 0/12 gold recovered, 3 derived, 3 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.647
- missed gold: C1, C2, C3, N1, N2, O1, R1, R2, R3, R4, R5, R7

### speclive-itself · mock · full (threshold 0.3)

- counts: 0/12 gold recovered, 3 derived, 3 spurious
- recall explicit=   0% paraphrased=   0%
- calibration: TP conf=0.0 FP conf=0.647
- missed gold: C1, C2, C3, N1, N2, O1, R1, R2, R3, R4, R5, R7

### warehouse-modernization · mock · segment (threshold 0.3)

- counts: 3/11 gold recovered, 5 derived, 2 spurious
- recall explicit=  27% paraphrased=   0%
- calibration: TP conf=0.83 FP conf=0.81
- missed gold: CON-003, CON-004, OBJ-001, Q-005, Q-006, REQ-010, REQ-012, RISK-007

### warehouse-modernization · mock · window (threshold 0.3)

- counts: 3/11 gold recovered, 5 derived, 2 spurious
- recall explicit=  27% paraphrased=   0%
- calibration: TP conf=0.83 FP conf=0.81
- missed gold: CON-003, CON-004, OBJ-001, Q-005, Q-006, REQ-010, REQ-012, RISK-007

### warehouse-modernization · mock · full (threshold 0.3)

- counts: 3/11 gold recovered, 5 derived, 2 spurious
- recall explicit=  27% paraphrased=   0%
- calibration: TP conf=0.83 FP conf=0.81
- missed gold: CON-003, CON-004, OBJ-001, Q-005, Q-006, REQ-010, REQ-012, RISK-007
