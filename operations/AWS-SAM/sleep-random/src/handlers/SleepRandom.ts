import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';

// Utility function to sleep for specified seconds
const sleep = (seconds :number) => new Promise(resolve => setTimeout(resolve, seconds * 1000));

// Utility function to safely parse JSON
const tryParseJSON = (data: unknown) :any => {
    try {
        console.log( typeof data )
        if ( typeof data === 'string' ) { return JSON.parse(data) }
        if ( typeof data === 'object' ) { return data; }
        console.log("UNKNOWN type of data!!!!!!!!!!!!!!!!!!!!!!!")
        return `${data}`;
    } catch (e) {
        console.log(`Error parsing Lambda-input!!`);
        console.log(`Data: ${data}`);
        return null;
    }
};

interface SleepConfig {
    'sleep-for-secs'?: number;
    sleepForSecs?: number;
    SleepForSecs?: number;
    'max-random-sleep-time'?: number;
    maxRandomSleepTime?: number;
    MaxRandomSleepTime?: number;
}

export async function handler(
    event: APIGatewayProxyEvent
  ): Promise<APIGatewayProxyResult> {
    let parsedEvent;
    try {
        // Parse event if it's a string, otherwise use as-is
        parsedEvent = event.body ? tryParseJSON(event.body) : event;
    } catch (e) {
        console.log(`Invalid Lambda-input!!`);
        parsedEvent = {}
    }
    try {
        // Check parsedEvent with variations in json-key-name
        let eventSleepTime: number | undefined;
        let maxRandomSleepTime = 5;

        if (typeof parsedEvent === 'object' && parsedEvent !== null) {
          const config = parsedEvent as SleepConfig;
          eventSleepTime = config['sleep-for-secs'] ||
                          config.sleepForSecs ||
                          config.SleepForSecs;

          maxRandomSleepTime = config['max-random-sleep-time'] ||
                              config.maxRandomSleepTime ||
                              config.MaxRandomSleepTime ||
                              5;
        } else if (typeof parsedEvent === 'string') {
          const numValue = Number(parsedEvent);
          if (!isNaN(numValue)) {
            eventSleepTime = numValue;
          }
        } else if (typeof parsedEvent === 'number') {
          eventSleepTime = parsedEvent;
        }

        // If sleep time is provided in parsedEvent, use it; otherwise generate random number
        const sleepTime = eventSleepTime !== undefined ?
            Number(eventSleepTime) :
            Math.floor(Math.random() * maxRandomSleepTime) + 1;

        // Validate sleep time is a positive number
        if (isNaN(sleepTime) || sleepTime <= 0) {
            throw new Error('Sleep time must be a positive number');
        }

        console.log(`Sleep time ${eventSleepTime !== undefined ? 'provided in event' : 'randomly generated'}: ${sleepTime} seconds (out of MAX ${maxRandomSleepTime}s)`);

        // Sleep for the specified duration
        await sleep(sleepTime);

        console.log(`Woke up after ${sleepTime} seconds`);

        return {
            statusCode: 200,
            body: JSON.stringify({
                message: `Successfully slept for ${sleepTime} seconds`,
                sleepTime: sleepTime,
                source: eventSleepTime !== undefined ? 'event' : 'random'
            })
        };
    } catch (error) {
        console.error('Error:', error);
        return {
            statusCode: error instanceof Error && error.message.includes('Sleep time must be') ? 400 : 500,
            body: JSON.stringify({
              message: error instanceof Error && error.message.includes('Sleep time must be') ?
                error.message :
                'Internal server error',
              error: error instanceof Error ? error.message : 'Unknown error'
            })
        };
    }
}

