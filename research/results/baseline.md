# Transcript → requirements: eval report

| case | provider | strategy | recall | wtd-recall | precision | F1 | type-acc | has-ev | correct-turn | grounded |
|------|----------|----------|--------|-----------|-----------|----|----------|--------|--------------|----------|
| iot-warehouse-ml | mock | segment |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| iot-warehouse-ml | mock | window |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |
| iot-warehouse-ml | mock | full |    0% |    0% |    0% |    0% |    0% |    0% |    0% |    0% |

## Per-run detail

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
