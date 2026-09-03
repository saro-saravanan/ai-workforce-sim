# Classifier audit: rules against the reviewer labels

120 statements (`docs/classifier-audit-sample.md`, labels in `docs/classifier-audit-labels.csv`). Precision: share of the statements the rules put on a channel that the reviewer put there too; recall: share of the reviewer's statements for a channel that the rules found.

## rules v2 (Phase 9): agreement 57%

| Channel | Assigned | Precision | Labelled | Recall |
|---|---|---|---|---|
| software | 24 | 83% | 34 | 59% |
| emb_driving | 24 | 38% | 11 | 82% |
| emb_manip | 24 | 25% | 12 | 50% |
| emb_fixed | 24 | 50% | 17 | 71% |
| emb_aerial | 1 | 100% | 2 | 50% |
| none | 23 | 91% | 44 | 48% |

## rules now: agreement 74%

| Channel | Assigned | Precision | Labelled | Recall |
|---|---|---|---|---|
| software | 41 | 73% | 34 | 88% |
| emb_driving | 14 | 71% | 11 | 91% |
| emb_manip | 18 | 44% | 12 | 67% |
| emb_fixed | 18 | 78% | 17 | 82% |
| emb_aerial | 1 | 100% | 2 | 50% |
| none | 28 | 93% | 44 | 59% |

## Remaining disagreements

| # | Occupation | Statement | Rules now | Reviewer |
|---|---|---|---|---|
| 9 | 19-4051 | Set control panel switches to route electric power from sources and direct particle beams through injector uni | software | emb_fixed |
| 12 | 25-2023 | Prepare students for later educational experiences by encouraging them to explore learning opportunities and t | software | none |
| 19 | 39-4021 | Act as pallbearers. | software | none |
| 20 | 39-5012 | Shape eyebrows and remove facial hair, using depilatory cream, tweezers, electrolysis or wax. | software | none |
| 25 | 11-9051 | Schedule and receive food and beverage deliveries, checking delivery contents to verify product quality and qu | software | none |
| 27 | 29-1126 | Transport patients to the hospital or within the hospital. | none | emb_manip |
| 29 | 33-3041 | Mark tires of parked vehicles with chalk and record time of marking, and return at regular intervals to ensure | emb_driving | software |
| 31 | 35-9021 | Load or unload trucks that deliver or pick up food or supplies. | emb_driving | emb_manip |
| 36 | 43-9031 | Transmit, deliver, or mail publication master to printer for production into film and plates. | emb_driving | software |
| 37 | 43-9051 | Contact delivery or courier services to arrange delivery of letters and parcels. | emb_manip | software |
| 45 | 53-6051 | Inspect repairs to transportation vehicles or equipment to ensure that repair work was performed properly. | emb_manip | none |
| 47 | 53-7064 | Transport packages to customers' vehicles. | emb_driving | emb_manip |
| 54 | 17-3024 | Select and use laboratory, operational, or diagnostic techniques or test equipment to assess electromechanical | software | none |
| 56 | 19-4051 | Perform testing, maintenance, repair, or upgrading of accelerator systems. | software | none |
| 65 | 51-4121 | Connect and turn regulator valves to activate and adjust gas flow and pressure so that desired flames are obta | emb_manip | emb_fixed |
| 67 | 51-6031 | Fold or stretch edges or lengths of items while sewing to facilitate forming specified sections. | emb_manip | emb_fixed |
| 70 | 53-1041 | Direct ground crews in the loading, unloading, securing, or staging of aircraft cargo or baggage. | emb_manip | none |
| 72 | 53-5022 | Follow safety procedures to ensure the protection of passengers, cargo, and vessels. | software | none |
| 73 | 19-4051 | Monitor nuclear reactor equipment performance to identify operational inefficiencies, hazards, or needs for ma | emb_fixed | software |
| 76 | 33-9032 | Inspect and adjust security systems, equipment, or machinery to ensure operational use and to detect evidence  | software | none |
| 78 | 45-2091 | Load and unload crops or containers of materials, manually or using conveyors, handtrucks, forklifts, or trans | emb_fixed | emb_manip |
| 79 | 49-1011 | Perform skilled repair or maintenance operations, using equipment such as hand or power tools, hydraulic press | emb_manip | none |
| 80 | 49-9012 | Clean plant growth, scale, paint, soil, or rust from meter housings, using wire brushes, scrapers, buffers, sa | emb_manip | none |
| 82 | 49-9091 | Adjust and repair coin, vending, or amusement machines and meters and replace defective mechanical and electri | emb_manip | none |
| 89 | 51-9032 | Clean and lubricate cutting machines, conveyors, blades, saws, or knives, using steam hoses, scrapers, brushes | emb_fixed | none |
| 96 | 53-7071 | Clean, lubricate, and adjust equipment, and replace filters and gaskets, using hand tools. | emb_fixed | none |
| 104 | 45-4011 | Spray or inject vegetation with insecticides to kill insects or to protect against disease or with herbicides  | none | emb_aerial |
| 109 | 47-2073 | Coordinate machine actions with other activities, positioning or moving loads in response to hand or audio sig | software | emb_driving |
| 111 | 47-2161 | Mix mortar and plaster to desired consistency or direct workers who perform mixing. | software | none |
| 112 | 49-3011 | Assemble and install electrical, plumbing, mechanical, hydraulic, and structural components and accessories, u | emb_manip | none |
| 116 | 49-9062 | Disassemble malfunctioning equipment and remove, repair, or replace defective parts, such as motors, clutches, | emb_manip | none |
