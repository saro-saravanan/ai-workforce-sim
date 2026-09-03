# Classifier audit sample

120 O*NET task statements sampled from `data/processed/tasks.csv` with seed 20260903, stratified by the channel the keyword rules assigned (`aiwsim diag classifier-sample --n 120 --seed 20260903`; review §2.4 item 3). Counts by assigned channel: software 24, emb_driving 24, emb_manip 24, emb_fixed 24, emb_aerial 1, none 23.

Fill the last column by hand with one of: `software` (screen work an AI system can do), `emb_driving` (a vehicle drives), `emb_manip` (a mobile manipulator or humanoid handles objects in a semi-structured setting), `emb_fixed` (fixed automation in a structured line or cell), `emb_aerial` (a drone), `none` (care, dexterity, safety-critical or unstructured bodily work outside the embodied horizon at central). Precision and recall per channel follow from the two columns; the sample is not labelled by the model's authors.

| # | Occupation | Task statement | Assigned channel | Human label |
|---|---|---|---|---|
| 1 | 11-9031 Education and Childcare Administrators, Preschool and Daycare | Prepare and maintain attendance, activity, planning, accounting, or personnel reports and records for officials and agencies, or direct preparation and maintenance activities. | software |  |
| 2 | 13-1020 Buyers and Purchasing Agents | Analyze price proposals, financial reports, and other data and information to determine reasonable prices. | software |  |
| 3 | 15-1299 Computer Occupations, All Other | Automate the deployment of software updates over geographically distributed network nodes. | software |  |
| 4 | 15-2051 Data Scientists | Clean and manipulate raw data using statistical software. | software |  |
| 5 | 17-2021 Agricultural Engineers | Discuss plans with clients, contractors, consultants, and other engineers so that they can be evaluated and necessary changes made. | software |  |
| 6 | 17-3025 Environmental Engineering Technologists and Technicians | Review work plans to schedule activities. | software |  |
| 7 | 17-3026 Industrial Engineering Technologists and Technicians | Adhere to all applicable regulations, policies, and procedures for health, safety, and environmental compliance. | software |  |
| 8 | 19-2041 Environmental Scientists and Specialists, Including Health | Provide industrial managers with technical materials on environmental issues, regulatory guidelines, or compliance actions. | software |  |
| 9 | 19-4051 Nuclear Technicians | Set control panel switches to route electric power from sources and direct particle beams through injector units. | software |  |
| 10 | 21-1091 Health Education Specialists | Develop and maintain health education libraries to provide resources for staff and community agencies. | software |  |
| 11 | 25-1111 Criminal Justice and Law Enforcement Teachers, Postsecondary | Compile, administer, and grade examinations, or assign this work to others. | software |  |
| 12 | 25-2023 Career/Technical Education Teachers, Middle School | Prepare students for later educational experiences by encouraging them to explore learning opportunities and to persevere with challenging tasks. | software |  |
| 13 | 25-3011 Adult Basic Education, Adult Secondary Education, and English as a Second Language Instructors | Prepare and implement remedial programs for students requiring extra help. | software |  |
| 14 | 25-4022 Librarians and Media Collections Specialists | Confer with colleagues, faculty, and community members and organizations to conduct informational programs, make collection decisions, and determine library services to offer. | software |  |
| 15 | 27-2032 Choreographers | Read and study story lines and musical scores to determine how to translate ideas and moods into dance movements. | software |  |
| 16 | 27-3043 Writers and Authors | Edit or rewrite existing written material as necessary, and submit written material for approval by supervisor, editor, or publisher. | software |  |
| 17 | 29-2051 Dietetic Technicians | Refer patients to other relevant services to provide continuity of care. | software |  |
| 18 | 35-2012 Cooks, Institution and Cafeteria | Compile and maintain records of food use and expenditures. | software |  |
| 19 | 39-4021 Funeral Attendants | Act as pallbearers. | software |  |
| 20 | 39-5012 Hairdressers, Hairstylists, and Cosmetologists | Shape eyebrows and remove facial hair, using depilatory cream, tweezers, electrolysis or wax. | software |  |
| 21 | 41-9041 Telemarketers | Obtain customer information such as name, address, and payment method, and enter orders into computers. | software |  |
| 22 | 43-2011 Switchboard Operators, Including Answering Service | Keep records of calls placed and charges incurred. | software |  |
| 23 | 43-5011 Cargo and Freight Agents | Enter shipping information into a computer by hand or by a hand-held scanner that reads bar codes on goods. | software |  |
| 24 | 51-9195 Molders, Shapers, and Casters, Except Metal and Plastic | Design spaces to display pottery for sale. | software |  |
| 25 | 11-9051 Food Service Managers | Schedule and receive food and beverage deliveries, checking delivery contents to verify product quality and quantity. | emb_driving |  |
| 26 | 27-2091 Disc Jockeys, Except Radio | Collect payments from customers. | emb_driving |  |
| 27 | 29-1126 Respiratory Therapists | Transport patients to the hospital or within the hospital. | emb_driving |  |
| 28 | 33-1011 First-Line Supervisors of Correctional Officers | Transfer or transport offenders on foot or by driving vehicles, such as trailers, vans, or buses. | emb_driving |  |
| 29 | 33-3041 Parking Enforcement Workers | Mark tires of parked vehicles with chalk and record time of marking, and return at regular intervals to ensure that parking time limits are not exceeded. | emb_driving |  |
| 30 | 33-9032 Security Guards | Escort or drive motor vehicle to transport individuals to specified locations or to provide personal protection. | emb_driving |  |
| 31 | 35-9021 Dishwashers | Load or unload trucks that deliver or pick up food or supplies. | emb_driving |  |
| 32 | 37-3013 Tree Trimmers and Pruners | Operate boom trucks, loaders, stump chippers, brush chippers, tractors, power saws, trucks, sprayers, and other equipment and tools. | emb_driving |  |
| 33 | 43-4141 New Accounts Clerks | Collect and record customer deposits and fees and issue receipts, using computers. | emb_driving |  |
| 34 | 43-5021 Couriers and Messengers | Plan and follow the most efficient routes for delivering goods. | emb_driving |  |
| 35 | 43-5111 Weighers, Measurers, Checkers, and Samplers, Recordkeeping | Transport materials, products, or samples to processing, shipping, or storage areas, manually or using conveyors, pumps, or hand trucks. | emb_driving |  |
| 36 | 43-9031 Desktop Publishers | Transmit, deliver, or mail publication master to printer for production into film and plates. | emb_driving |  |
| 37 | 43-9051 Mail Clerks and Mail Machine Operators, Except Postal Service | Contact delivery or courier services to arrange delivery of letters and parcels. | emb_driving |  |
| 38 | 47-2073 Operating Engineers and Other Construction Equipment Operators | Drive tractor-trailer trucks to move equipment from site to site. | emb_driving |  |
| 39 | 47-4071 Septic Tank Servicers and Sewer Pipe Cleaners | Drive trucks to transport crews, materials, and equipment. | emb_driving |  |
| 40 | 49-9097 Signal and Track Switch Repairers | Drive motor vehicles to job sites. | emb_driving |  |
| 41 | 51-3021 Butchers and Meat Cutters | Total sales, and collect money from customers. | emb_driving |  |
| 42 | 51-9051 Furnace, Kiln, Oven, Drier, and Kettle Operators and Tenders | Transport materials and products to and from work areas, manually or using carts, handtrucks, or hoists. | emb_driving |  |
| 43 | 53-3032 Heavy and Tractor-Trailer Truck Drivers | Plan or adjust routes based on changing conditions, using computer equipment, global positioning systems (GPS) equipment, or other navigation devices, to minimize fuel consumption and carbon emissions. | emb_driving |  |
| 44 | 53-6021 Parking Attendants | Explain and calculate parking charges, collect fees from customers, and respond to customer complaints. | emb_driving |  |
| 45 | 53-6051 Transportation Inspectors | Inspect repairs to transportation vehicles or equipment to ensure that repair work was performed properly. | emb_driving |  |
| 46 | 53-6061 Passenger Attendants | Issue and collect passenger boarding passes and transfers, tearing or punching tickets as necessary to prevent reuse. | emb_driving |  |
| 47 | 53-7064 Packers and Packagers, Hand | Transport packages to customers' vehicles. | emb_driving |  |
| 48 | 53-7081 Refuse and Recyclable Material Collectors | Drive trucks, following established routes, through residential streets or alleys or through business or industrial areas. | emb_driving |  |
| 49 | 11-3051 Industrial Production Managers | Perform or direct preventive or corrective containment or cleanup to protect the environment. | emb_manip |  |
| 50 | 11-3121 Human Resources Managers | Plan and conduct new employee orientation to foster positive attitude toward organizational objectives. | emb_manip |  |
| 51 | 11-9121 Natural Sciences Managers | Conduct, or oversee the conduct of, chemical, physical, and biological water quality monitoring or sampling to ensure compliance with water quality standards. | emb_manip |  |
| 52 | 15-1254 Web Developers | Install and configure hypertext transfer protocol (HTTP) servers and associated operating systems. | emb_manip |  |
| 53 | 17-2199 Engineers, All Other | Research or develop emerging microelectromechanical (MEMS) systems to convert nontraditional energy sources into power, such as ambient energy harvesters that convert environmental vibrations into usable energy. | emb_manip |  |
| 54 | 17-3024 Electro-Mechanical and Mechatronics Technologists and Technicians | Select and use laboratory, operational, or diagnostic techniques or test equipment to assess electromechanical circuits, equipment, processes, systems, or subsystems. | emb_manip |  |
| 55 | 19-4043 Geological Technicians, Except Hydrologic Technicians | Plan and direct activities of workers who operate equipment to collect data. | emb_manip |  |
| 56 | 19-4051 Nuclear Technicians | Perform testing, maintenance, repair, or upgrading of accelerator systems. | emb_manip |  |
| 57 | 29-1124 Radiation Therapists | Calculate actual treatment dosages delivered during each session. | emb_manip |  |
| 58 | 43-9051 Mail Clerks and Mail Machine Operators, Except Postal Service | Operate embossing machines or typewriters to make corrections, additions, and changes to address plates. | emb_manip |  |
| 59 | 45-4022 Logging Equipment Operators | Drive tractors for building or repairing logging and skid roads. | emb_manip |  |
| 60 | 47-3014 Helpers--Painters, Paperhangers, Plasterers, and Stucco Masons | Remove articles such as cabinets, metal furniture, and paint containers from stripping tanks after prescribed periods of time. | emb_manip |  |
| 61 | 47-4090 Miscellaneous Construction and Related Workers | Install storm windows or storm doors and verify proper fit. | emb_manip |  |
| 62 | 47-5071 Roustabouts, Oil and Gas | Move pipes to and from trucks, using truck winches and motorized lifts, or by hand. | emb_manip |  |
| 63 | 49-3093 Tire Repairers and Changers | Clean sides of whitewall tires. | emb_manip |  |
| 64 | 51-4033 Grinding, Lapping, Polishing, and Buffing Machine Tool Setters, Operators, and Tenders, Metal and Plastic | Activate machine start-up switches to grind, lap, hone, debar, shear, or cut workpieces, according to specifications. | emb_manip |  |
| 65 | 51-4121 Welders, Cutters, Solderers, and Brazers | Connect and turn regulator valves to activate and adjust gas flow and pressure so that desired flames are obtained. | emb_manip |  |
| 66 | 51-4192 Layout Workers, Metal and Plastic | Install doors, hatches, brackets, and clips. | emb_manip |  |
| 67 | 51-6031 Sewing Machine Operators | Fold or stretch edges or lengths of items while sewing to facilitate forming specified sections. | emb_manip |  |
| 68 | 51-9021 Crushing, Grinding, and Polishing Machine Setters, Operators, and Tenders | Clean work areas. | emb_manip |  |
| 69 | 51-9023 Mixing and Blending Machine Setters, Operators, and Tenders | Transfer materials, supplies, or products between work areas, using moving equipment or hand tools. | emb_manip |  |
| 70 | 53-1041 Aircraft Cargo Handling Supervisors | Direct ground crews in the loading, unloading, securing, or staging of aircraft cargo or baggage. | emb_manip |  |
| 71 | 53-1047 First-Line Supervisors of Transportation and Material Moving Workers, Except Aircraft Cargo Handling Supervisors | Inspect job sites to determine the extent of maintenance or repairs needed. | emb_manip |  |
| 72 | 53-5022 Motorboat Operators | Follow safety procedures to ensure the protection of passengers, cargo, and vessels. | emb_manip |  |
| 73 | 19-4051 Nuclear Technicians | Monitor nuclear reactor equipment performance to identify operational inefficiencies, hazards, or needs for maintenance or repair. | emb_fixed |  |
| 74 | 19-4051 Nuclear Technicians | Set up equipment that automatically detects area radiation deviations and test detection equipment to ensure its accuracy. | emb_fixed |  |
| 75 | 31-1131 Nursing Assistants | Set up treating or testing equipment, such as oxygen tents, portable radiograph (x-ray) equipment, or overhead irrigation bottles, as directed by a physician or nurse. | emb_fixed |  |
| 76 | 33-9032 Security Guards | Inspect and adjust security systems, equipment, or machinery to ensure operational use and to detect evidence of tampering. | emb_fixed |  |
| 77 | 39-9032 Recreation Workers | Provide for entertainment and set up related decorations and equipment. | emb_fixed |  |
| 78 | 45-2091 Agricultural Equipment Operators | Load and unload crops or containers of materials, manually or using conveyors, handtrucks, forklifts, or transfer augers. | emb_fixed |  |
| 79 | 49-1011 First-Line Supervisors of Mechanics, Installers, and Repairers | Perform skilled repair or maintenance operations, using equipment such as hand or power tools, hydraulic presses or shears, or welding equipment. | emb_fixed |  |
| 80 | 49-9012 Control and Valve Installers and Repairers, Except Mechanical Door | Clean plant growth, scale, paint, soil, or rust from meter housings, using wire brushes, scrapers, buffers, sandblasters, or cleaning compounds. | emb_fixed |  |
| 81 | 49-9052 Telecommunications Line Installers and Repairers | Set up service for customers, installing, connecting, testing, or adjusting equipment. | emb_fixed |  |
| 82 | 49-9091 Coin, Vending, and Amusement Machine Servicers and Repairers | Adjust and repair coin, vending, or amusement machines and meters and replace defective mechanical and electrical parts, using hand tools, soldering irons, and diagrams. | emb_fixed |  |
| 83 | 51-4072 Molding, Coremaking, and Casting Machine Setters, Operators, and Tenders, Metal and Plastic | Adjust equipment and workpiece holding fixtures, such as mold frames, tubs, and cutting tables, to ensure proper functioning. | emb_fixed |  |
| 84 | 51-4191 Heat Treating Equipment Setters, Operators, and Tenders, Metal and Plastic | Place completed workpieces on conveyors, using cold rods, tongs, or chain hoists, or signal crane operators to transport them to subsequent stations. | emb_fixed |  |
| 85 | 51-4191 Heat Treating Equipment Setters, Operators, and Tenders, Metal and Plastic | Set and adjust speeds of reels and conveyors for prescribed time cycles to pass parts through continuous furnaces. | emb_fixed |  |
| 86 | 51-4193 Plating Machine Setters, Operators, and Tenders, Metal and Plastic | Position and feed materials into processing machines, by hand or by using automated equipment. | emb_fixed |  |
| 87 | 51-4193 Plating Machine Setters, Operators, and Tenders, Metal and Plastic | Observe gauges to ensure that machines are operating properly, making adjustments or stopping machines when problems occur. | emb_fixed |  |
| 88 | 51-9022 Grinding and Polishing Workers, Hand | Load and adjust workpieces onto equipment or work tables, using hand tools. | emb_fixed |  |
| 89 | 51-9032 Cutting and Slicing Machine Setters, Operators, and Tenders | Clean and lubricate cutting machines, conveyors, blades, saws, or knives, using steam hoses, scrapers, brushes, or oil cans. | emb_fixed |  |
| 90 | 51-9041 Extruding, Forming, Pressing, and Compacting Machine Setters, Operators, and Tenders | Feed products into machines by hand or conveyor. | emb_fixed |  |
| 91 | 51-9041 Extruding, Forming, Pressing, and Compacting Machine Setters, Operators, and Tenders | Thread extruded strips through water tanks and hold-down bars, or attach strands to wires and draw them through tubes. | emb_fixed |  |
| 92 | 51-9111 Packaging and Filling Machine Operators and Tenders | Supply materials to spindles, conveyors, hoppers, or other feeding devices and unload packaged product. | emb_fixed |  |
| 93 | 51-9141 Semiconductor Processing Technicians | Load semiconductor material into furnace. | emb_fixed |  |
| 94 | 51-9197 Tire Builders | Position ply stitcher rollers and drums according to width of stock, using hand tools and gauges. | emb_fixed |  |
| 95 | 53-7011 Conveyor Operators and Tenders | Operate elevator systems in conjunction with conveyor systems. | emb_fixed |  |
| 96 | 53-7071 Gas Compressor and Gas Pumping Station Operators | Clean, lubricate, and adjust equipment, and replace filters and gaskets, using hand tools. | emb_fixed |  |
| 97 | 17-1022 Surveyors | Direct aerial surveys of specified geographical areas. | emb_aerial |  |
| 98 | 29-1243 Pediatric Surgeons | Provide consultation and surgical assistance to other physicians and surgeons. | none |  |
| 99 | 29-1292 Dental Hygienists | Maintain dental equipment and sharpen and sterilize dental instruments. | none |  |
| 100 | 29-2031 Cardiovascular Technologists and Technicians | Inject contrast medium into patients' blood vessels. | none |  |
| 101 | 33-2011 Firefighters | Inspect fire sites after flames have been extinguished to ensure that there is no further danger. | none |  |
| 102 | 39-9011 Childcare Workers | Dress children and change diapers. | none |  |
| 103 | 45-2021 Animal Breeders | Clip or shear hair on animals. | none |  |
| 104 | 45-4011 Forest and Conservation Workers | Spray or inject vegetation with insecticides to kill insects or to protect against disease or with herbicides to reduce competing vegetation. | none |  |
| 105 | 47-2031 Carpenters | Follow established safety rules and regulations and maintain a safe and clean environment. | none |  |
| 106 | 47-2031 Carpenters | Install rough door and window frames, subflooring, fixtures, or temporary supports in structures undergoing construction or repair. | none |  |
| 107 | 47-2043 Floor Sanders and Finishers | Scrape and sand floor edges and areas inaccessible to floor sanders, using scrapers, disk-type sanders, and sandpaper. | none |  |
| 108 | 47-2061 Construction Laborers | Erect or dismantle scaffolding, shoring, braces, traffic barricades, ramps, or other temporary structures. | none |  |
| 109 | 47-2073 Operating Engineers and Other Construction Equipment Operators | Coordinate machine actions with other activities, positioning or moving loads in response to hand or audio signals from crew members. | none |  |
| 110 | 47-2081 Drywall and Ceiling Tile Installers | Nail channels or wood furring strips to surfaces to provide mounting for tile. | none |  |
| 111 | 47-2161 Plasterers and Stucco Masons | Mix mortar and plaster to desired consistency or direct workers who perform mixing. | none |  |
| 112 | 49-3011 Aircraft Mechanics and Service Technicians | Assemble and install electrical, plumbing, mechanical, hydraulic, and structural components and accessories, using hand or power tools. | none |  |
| 113 | 49-9021 Heating, Air Conditioning, and Refrigeration Mechanics and Installers | Install, connect, or adjust thermostats, humidistats, or timers. | none |  |
| 114 | 49-9041 Industrial Machinery Mechanics | Repair or replace broken or malfunctioning components of machinery or equipment. | none |  |
| 115 | 49-9052 Telecommunications Line Installers and Repairers | Lay underground cable directly in trenches, or string it through conduits running through trenches. | none |  |
| 116 | 49-9062 Medical Equipment Repairers | Disassemble malfunctioning equipment and remove, repair, or replace defective parts, such as motors, clutches, or transformers. | none |  |
| 117 | 49-9063 Musical Instrument Repairers and Tuners | Polish instruments, using rags and polishing compounds, buffing wheels, or burnishing tools. | none |  |
| 118 | 49-9071 Maintenance and Repair Workers, General | Repair machines, equipment, or structures, using tools such as hammers, hoists, saws, drills, wrenches, or equipment such as precision measuring instruments or electrical or electronic testing devices. | none |  |
| 119 | 49-9094 Locksmiths and Safe Repairers | Insert new or repaired tumblers into locks to change combinations. | none |  |
| 120 | 51-9081 Dental Laboratory Technicians | Prepare metal surfaces for bonding with porcelain to create artificial teeth, using small hand tools. | none |  |
