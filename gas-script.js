function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('Custom Menu')
      .addItem('Do Something', 'doSomething')
      .addToUi();
}

function doSomething() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  sheet.appendRow(['Hello, World!', new Date()]);
}

function onEdit(e) {
  var range = e.range;
  var newValue = e.value;
  var sheet = e.source.getActiveSheet();

  // For example, log every edit
  Logger.log('Edited cell: ' + range.getA1Notation() + ' New value: ' + newValue);
}

function setTriggers() {
  ScriptApp.newTrigger('onEdit')
      .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
      .onEdit()
      .create();
}