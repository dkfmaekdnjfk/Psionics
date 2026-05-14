#!/usr/bin/osascript -l JavaScript
ObjC.import("Foundation");

const app = Application.currentApplication();
app.includeStandardAdditions = true;

const calendarApp = Application("Calendar");

function isoString(dateValue) {
  if (!dateValue) return "";
  const d = new Date(dateValue);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString();
}

const now = new Date();
const windowDays = 30;
const rangeEnd = new Date(now.getTime() + windowDays * 24 * 60 * 60 * 1000);

const events = [];
calendarApp.calendars().forEach((calendar) => {
  const inRange = calendar.events.whose({
    startDate: { _greaterThanEquals: now },
    endDate: { _lessThanEquals: rangeEnd },
  })();

  inRange.forEach((event) => {
    events.push({
      calendar: calendar.name(),
      title: event.summary() || "",
      start: isoString(event.startDate()),
      end: isoString(event.endDate()),
      location: event.location() || "",
      allDay: Boolean(event.alldayEvent()),
      notes: event.description() || "",
    });
  });
});

events.sort((a, b) => a.start.localeCompare(b.start));

const payload = JSON.stringify(
  {
    exportedAt: new Date().toISOString(),
    windowDays,
    events,
  },
  null,
  2
);

const outputDir = "output/calendar";
const outputFile = `${outputDir}/events.json`;

$.NSFileManager.defaultManager.createDirectoryAtPathWithIntermediateDirectoriesAttributesError(
  outputDir,
  true,
  $(),
  null
);
$(payload).writeToFileAtomicallyEncodingError(
  outputFile,
  true,
  $.NSUTF8StringEncoding,
  null
);

console.log(`Wrote ${events.length} events to ${outputFile}`);
