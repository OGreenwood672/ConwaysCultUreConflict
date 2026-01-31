// import p5 from "p5";

import { CsvStreamer } from "./csv_streamer";
import type { Person } from "./person";

const SIM_LOG = "http://localhost:5173/logs/updates.csv";
const PERSON_CULTURE = "http://localhost:5173/logs/start.json";


export const sketch = (p: p5) => {

    let sim_log: CsvStreamer;
    let person_culture: any = {};

    let WIDTH = p.windowWidth * 0.95;
    let HEIGHT = p.windowHeight * 0.95;

    let buildings = [];

    const TIME_PER_TICK = 100;
    let curr_tick = 0;
    let curr_tick_actions: any[] = [];
    let last_tick_time = 0;
    let logEntry: any = null;

    p.preload = () => {
        console.log("Preloading...");
        // Load small file normally
        p.loadJSON(PERSON_CULTURE, (data: any[]) => {
            // data is already a standard JS array
            person_culture = data["bob"].reduce((acc: any, item: any) => {
                // Use direct property access (item.id), not .get()
                acc[item.id] = {
                    id: Number(item.id),
                    culture: Number(item.culture),
                    x: Number(item.initial_position[0]),
                    y: Number(item.initial_position[1]),
                };
                return acc;
            }, {});
            console.log(person_culture)
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
            curr_tick_actions = [];
            curr_tick++;
            while (logEntry && parseInt(logEntry.tick) === curr_tick) {
                curr_tick_actions.push(logEntry);
                logEntry = sim_log.getNextLine();
            }
        }

        for (let action of curr_tick_actions) {
            const person_id = parseInt(action.person_id);

            let person = person_culture[person_id];
            if (!person) continue;

            switch (action.action) {
                case "move":
                    person.x = parseFloat(action.new_x);
                    person.y = parseFloat(action.new_y);
                    break;
                case "build":
                    buildings.push({x: action.x, y: action.y});
                    break;
                case "die":
                    delete person_culture[person_id];
                    break;
                case "communicate":
                    break;
                case "add":
                    person_culture[person_id] = {
                        id: person_id,
                        culture: parseInt(action.culture),
                        x: parseFloat(action.x),
                        y: parseFloat(action.y),
                    };
                    break;
                default:
                    break;
            }
        
        }

        // Draw persons
        for (let key in person_culture) {
            const person: Person = person_culture[key];
            p.fill(person.culture * 50 % 255, 100, 255 - (person.culture * 50 % 255));
            p.circle(person.x, person.y, 5);
        }

        // Draw buildings
        p.fill(150);
        for (let building of buildings) {
            p.rect(building.x, building.y, 10, 10);
        }
        
    };
};