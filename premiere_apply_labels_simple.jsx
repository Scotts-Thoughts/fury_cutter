// Fury Cutter Label Applicator
// Uses keyboard shortcuts to apply labels to timeline clips
// 
// Two modes of operation:
// 1. AUTOMATIC: Script selects clips and sends keyboard shortcuts via PowerShell
// 2. EXPORT: Script exports a command file for the Python helper (more reliable)
//
// REQUIRED: Set up keyboard shortcuts in Premiere Pro first!
// Go to Edit > Keyboard Shortcuts and search for "label"
// Assign shortcuts for Edit > Label > [Color Name]

// ============================================================================
// CONFIGURATION - Customize these to match your Premiere Pro keyboard shortcuts
// ============================================================================

// Map label names to SendKeys format (^ = Ctrl, + = Shift, % = Alt)
// Default setup uses Ctrl+Shift+Number for label colors
var LABEL_SHORTCUTS = {
    // Primary battle types
    "Rival": "^+1",         // Ctrl+Shift+1
    "Gym": "^+2",           // Ctrl+Shift+2
    "E4": "^+3",            // Ctrl+Shift+3
    "Champion": "^+4",      // Ctrl+Shift+4
    "Postgame": "^+5",      // Ctrl+Shift+5
    "Enemy Leader": "^+6",  // Ctrl+Shift+6
    "Enemy Boss": "^+7",    // Ctrl+Shift+7
    
    // Fallback/default colors
    "Cerulean": "^+8",      // Ctrl+Shift+8
    "Caribbean": "^+9",     // Ctrl+Shift+9
    "Lavender": "^+0",      // Ctrl+Shift+0
    
    // Additional (assign F-keys if needed)
    "Magenta": "^+{F1}",
    "Purple": "^+{F2}",
    "Blue": "^+{F3}",
    "Green": "^+{F4}",      // Green from Timebolt format
    "Yellow": "^+{F5}",
    "Brown": "^+{F6}"
};

// Offset in seconds to jump INTO the clip (not at the very start)
var OFFSET_SECONDS = 0.5;

// Delays in milliseconds
var KEY_DELAY_MS = 100;
var CLIP_DELAY_MS = 200;

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function secondsToTicks(s) { 
    return s * 254016000000; 
}

function clearSelection(seq) {
    for (var t = 0; t < seq.videoTracks.numTracks; t++) {
        var track = seq.videoTracks[t];
        for (var c = 0; c < track.clips.numItems; c++) {
            try { track.clips[c].setSelected(false, true); } catch(e) {}
        }
    }
}

// Parse JSON file - handles both Timebolt and Automation Blocks formats
function parseLabelsJSON(content) {
    var data;
    try {
        data = eval("(" + content + ")");
    } catch(e) {
        return { error: "Failed to parse JSON: " + e.message };
    }
    
    var labels = [];
    
    // Check for Automation Blocks format: { "labels": [...] }
    if (data.labels && data.labels.length > 0) {
        for (var i = 0; i < data.labels.length; i++) {
            var entry = data.labels[i];
            labels.push({
                start_seconds: entry.start_seconds,
                label: entry.label,
                trainer: entry.trainer || "Unknown"
            });
        }
        return { labels: labels, format: "automation_blocks" };
    }
    
    // Check for Timebolt format: flat array with "label" and "name" properties
    if (data.length && data.length > 0) {
        for (var i = 0; i < data.length; i++) {
            var entry = data[i];
            // Only include entries that have a label
            if (entry.label) {
                labels.push({
                    start_seconds: entry.start,
                    label: entry.label,
                    trainer: entry.name || "Unknown"
                });
            }
        }
        return { labels: labels, format: "timebolt" };
    }
    
    return { error: "Unknown JSON format - expected 'labels' array or Timebolt format" };
}

// ============================================================================
// KEYBOARD SHORTCUT FUNCTIONS
// ============================================================================

// Send keyboard shortcut using PowerShell (Windows only)
function sendKeys(keys) {
    var psCommand = 'powershell -Command "Add-Type -AssemblyName System.Windows.Forms; ' +
                    '[System.Windows.Forms.SendKeys]::SendWait(\'' + keys + '\')"';
    
    try {
        system.callSystem(psCommand);
        return true;
    } catch(e) {
        return false;
    }
}

// Focus the timeline panel with Shift+3
function focusTimeline() {
    sendKeys("+3"); // Shift+3
    $.sleep(KEY_DELAY_MS);
}

// ============================================================================
// CLIP SELECTION AND LABEL APPLICATION
// ============================================================================

function selectClipAtTime(seq, seconds) {
    var targetSeconds = seconds + OFFSET_SECONDS;
    var ticks = secondsToTicks(targetSeconds);
    
    // Move playhead
    seq.setPlayerPosition(ticks.toString());
    
    // Clear selection
    clearSelection(seq);
    
    // Find and select clip at playhead (check all video tracks)
    for (var t = 0; t < seq.videoTracks.numTracks; t++) {
        var track = seq.videoTracks[t];
        for (var c = 0; c < track.clips.numItems; c++) {
            var clip = track.clips[c];
            if (clip.start.ticks <= ticks && clip.end.ticks > ticks) {
                try {
                    clip.setSelected(true, true);
                    return {
                        success: true,
                        clipName: clip.name,
                        time: targetSeconds
                    };
                } catch(e) {
                    return { success: false, error: e.toString() };
                }
            }
        }
    }
    return { success: false, error: "No clip at " + targetSeconds.toFixed(2) + "s" };
}

function applyLabelViaShortcut(labelName) {
    var shortcut = LABEL_SHORTCUTS[labelName];
    
    if (!shortcut) {
        // Try case-insensitive lookup
        for (var key in LABEL_SHORTCUTS) {
            if (key.toLowerCase() === labelName.toLowerCase()) {
                shortcut = LABEL_SHORTCUTS[key];
                break;
            }
        }
    }
    
    if (!shortcut) {
        return { success: false, error: "No shortcut for label: " + labelName };
    }
    
    // Focus timeline and send shortcut
    focusTimeline();
    var keySent = sendKeys(shortcut);
    
    return { 
        success: keySent, 
        shortcut: shortcut,
        error: keySent ? null : "Failed to send shortcut"
    };
}

// ============================================================================
// EXPORT FOR PYTHON HELPER
// ============================================================================

function exportForPython(labels, outputPath) {
    // Create a Python-compatible JSON file with all the info needed
    var pyData = {
        clips: [],
        shortcuts: LABEL_SHORTCUTS
    };
    
    for (var i = 0; i < labels.length; i++) {
        var entry = labels[i];
        pyData.clips.push({
            start_seconds: entry.start_seconds + OFFSET_SECONDS,
            label: entry.label,
            trainer: entry.trainer,
            shortcut: LABEL_SHORTCUTS[entry.label] || "^+8" // Default to Cerulean
        });
    }
    
    var jsonStr = "{\n";
    jsonStr += '  "offset_seconds": ' + OFFSET_SECONDS + ',\n';
    jsonStr += '  "key_delay_ms": ' + KEY_DELAY_MS + ',\n';
    jsonStr += '  "clip_delay_ms": ' + CLIP_DELAY_MS + ',\n';
    jsonStr += '  "clips": [\n';
    
    for (var i = 0; i < pyData.clips.length; i++) {
        var c = pyData.clips[i];
        jsonStr += '    {\n';
        jsonStr += '      "start_seconds": ' + c.start_seconds + ',\n';
        jsonStr += '      "label": "' + c.label + '",\n';
        jsonStr += '      "trainer": "' + c.trainer + '",\n';
        jsonStr += '      "shortcut": "' + c.shortcut + '"\n';
        jsonStr += '    }';
        if (i < pyData.clips.length - 1) jsonStr += ',';
        jsonStr += '\n';
    }
    
    jsonStr += '  ]\n';
    jsonStr += '}\n';
    
    var f = new File(outputPath);
    f.open("w");
    f.write(jsonStr);
    f.close();
    
    return outputPath;
}

// ============================================================================
// MAIN EXECUTION
// ============================================================================

var seq = app.project.activeSequence;
if (!seq) { 
    alert("No active sequence!\n\nPlease open a sequence first."); 
} else {
    // Show mode selection dialog
    var modeDialog = new Window('dialog', 'Fury Cutter - Label Application Mode');
    modeDialog.add('statictext', undefined, 'Choose how to apply labels:');
    modeDialog.add('statictext', undefined, '');
    
    var autoBtn = modeDialog.add('button', undefined, 'AUTOMATIC (Script sends keys)');
    var exportBtn = modeDialog.add('button', undefined, 'EXPORT (Use Python helper)');
    var cancelBtn = modeDialog.add('button', undefined, 'Cancel');
    
    modeDialog.add('statictext', undefined, '');
    modeDialog.add('statictext', undefined, 'Automatic: Script will send keyboard shortcuts directly.');
    modeDialog.add('statictext', undefined, 'Export: Creates file for Python helper (more reliable).');
    
    var selectedMode = null;
    autoBtn.onClick = function() { selectedMode = 'auto'; modeDialog.close(); };
    exportBtn.onClick = function() { selectedMode = 'export'; modeDialog.close(); };
    cancelBtn.onClick = function() { modeDialog.close(); };
    
    modeDialog.show();
    
    if (selectedMode) {
        var f = File.openDialog("Select Fury Cutter JSON", "*.json");
        if (f) {
            f.open("r"); 
            var content = f.read();
            f.close();
            
            var parsed = parseLabelsJSON(content);
            
            if (parsed.error) {
                alert("Error: " + parsed.error);
            } else if (parsed.labels.length === 0) {
                alert("No labeled segments found in JSON file.");
            } else {
                var labels = parsed.labels;
                
                if (selectedMode === 'export') {
                    // Export mode - create file for Python helper
                    var exportPath = f.path + "/" + f.name.replace(".json", "_premiere_labels.json");
                    exportForPython(labels, exportPath);
                    
                    var msg = "EXPORT COMPLETE\n";
                    msg += "================\n\n";
                    msg += "Exported " + labels.length + " clips to:\n";
                    msg += exportPath + "\n\n";
                    msg += "Now run the Python helper:\n";
                    msg += "  python premiere_label_sender.py \"" + exportPath + "\"\n\n";
                    msg += "The Python script will:\n";
                    msg += "1. Wait for you to focus Premiere Pro\n";
                    msg += "2. Navigate to each clip and apply labels via keyboard shortcuts";
                    
                    alert(msg);
                    
                } else {
                    // Automatic mode - apply labels directly
                    var setupMsg = "KEYBOARD SHORTCUT SETUP REQUIRED\n";
                    setupMsg += "=================================\n\n";
                    setupMsg += "Ensure you have keyboard shortcuts set in Premiere Pro:\n";
                    setupMsg += "Edit > Keyboard Shortcuts > search 'label'\n\n";
                    setupMsg += "Required shortcuts:\n";
                    setupMsg += "  Ctrl+Shift+1 = Rival\n";
                    setupMsg += "  Ctrl+Shift+2 = Gym\n";
                    setupMsg += "  Ctrl+Shift+3 = E4\n";
                    setupMsg += "  Ctrl+Shift+4 = Champion\n";
                    setupMsg += "  Ctrl+Shift+5 = Postgame\n";
                    setupMsg += "  Ctrl+Shift+6 = Enemy Leader\n";
                    setupMsg += "  Ctrl+Shift+7 = Enemy Boss\n";
                    setupMsg += "  Ctrl+Shift+8 = Cerulean (default)\n\n";
                    setupMsg += "Found " + labels.length + " clips to label.\n";
                    setupMsg += "Click OK to start (keep Premiere focused!)";
                    
                    alert(setupMsg);
                    
                    // Brief pause before starting
                    $.sleep(1000);
                    
                    var successCount = 0;
                    var failCount = 0;
                    var details = [];
                    
                    for (var i = 0; i < labels.length; i++) {
                        var entry = labels[i];
                        
                        // Select the clip
                        var selectResult = selectClipAtTime(seq, entry.start_seconds);
                        
                        if (!selectResult.success) {
                            failCount++;
                            details.push("- " + entry.trainer + ": " + selectResult.error);
                            continue;
                        }
                        
                        // Apply label via shortcut
                        var labelResult = applyLabelViaShortcut(entry.label);
                        
                        if (labelResult.success) {
                            successCount++;
                            details.push("+ " + entry.trainer + " -> " + entry.label);
                        } else {
                            failCount++;
                            details.push("- " + entry.trainer + ": " + labelResult.error);
                        }
                        
                        $.sleep(CLIP_DELAY_MS);
                    }
                    
                    // Show results
                    var report = "LABEL APPLICATION COMPLETE\n";
                    report += "===========================\n\n";
                    report += "Success: " + successCount + " / " + labels.length + "\n";
                    report += "Failed: " + failCount + "\n\n";
                    
                    if (details.length <= 20) {
                        report += "Details:\n";
                        for (var j = 0; j < details.length; j++) {
                            report += details[j] + "\n";
                        }
                    } else {
                        report += "First 20 results:\n";
                        for (var j = 0; j < 20; j++) {
                            report += details[j] + "\n";
                        }
                        report += "... and " + (details.length - 20) + " more\n";
                    }
                    
                    if (failCount > 0) {
                        report += "\n===========================\n";
                        report += "TROUBLESHOOTING:\n";
                        report += "- Make sure keyboard shortcuts are assigned in Premiere\n";
                        report += "- Try the EXPORT mode with Python helper instead\n";
                        report += "- Check that Premiere was the active window";
                    }
                    
                    alert(report);
                }
            }
        }
    }
}
