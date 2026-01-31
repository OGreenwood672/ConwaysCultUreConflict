// import p5 from "p5";

import { CsvStreamer } from "./csv_streamer";
import type { Person } from "./person";



const SIM_LOG = "http://localhost:5173/sim_log.csv";
const PERSON_CULTURE = "http://localhost:5173/person_culture.csv";


export const sketch = (p: p5) => {

    let sim_log: CsvStreamer;
    let person_culture: Object = {};    

    let WIDTH = p.windowWidth * 0.95;
    let HEIGHT = p.windowHeight * 0.95;

    let people: Person[] = [];

    const TIME_PER_TICK = 100;
    let curr_tick = 0;
    let curr_tick_actions = [];
    let last_tick_time = 0;
    let logEntry: any = null;

    p.preload = () => {
        console.log("Preloading...");
        // Load small file normally
        p.loadTable(PERSON_CULTURE, "csv", "header", (table) => {
            person_culture = table.rows.reduce((acc: any, row: any) => {
                // Adjust index based on your CSV structure (p5.Table uses .get())
                acc[row.get(0)] = Person {
                    id: parseInt(row.get(0)),
                    culture: row.get(1),
                    x: parseFloat(row.get(2)),
                    y: parseFloat(row.get(3)),
                };
                return acc;
            }, {});
        });
    };

    p.setup = () => {
        p.createCanvas(WIDTH + 1, HEIGHT + 1);
        p.background(0);
        
        // Initialize the streamer for the massive file
        sim_log = new CsvStreamer(SIM_LOG);
        sim_log.start();

        logEntry = sim_log.getNextLine();

        console.log("setup complete");
    };

    p.draw = () => {

        p.background(0);
        
        if (last_tick_time + TIME_PER_TICK < p.millis()) {
            last_tick_time = p.millis();
            curr_tick++;
            while (logEntry && parseInt(logEntry.tick) === curr_tick) {
                logEntry = sim_log.getNextLine();
                curr_tick_actions.push(logEntry);
            }
        }

        for (let action of curr_tick_actions) {
            const person_id = parseInt(action.person_id);
            const x = parseFloat(action.x);
            const y = parseFloat(action.y);
            const culture = person_culture[person_id] || "unknown";

            // Draw person


        
    };
};