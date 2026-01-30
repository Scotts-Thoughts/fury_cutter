/**
 * Fury Cutter Labels - Host Script
 * Tries multiple methods to execute label commands
 */

function secondsToTicks(seconds) {
    return seconds * 254016000000;
}

function clearSelections() {
    var seq = app.project.activeSequence;
    if (!seq) return;
    for (var t = 0; t < seq.videoTracks.numTracks; t++) {
        var track = seq.videoTracks[t];
        for (var c = 0; c < track.clips.numItems; c++) {
            try { track.clips[c].setSelected(false, false); } catch(e) {}
        }
    }
    for (var t = 0; t < seq.audioTracks.numTracks; t++) {
        var track = seq.audioTracks[t];
        for (var c = 0; c < track.clips.numItems; c++) {
            try { track.clips[c].setSelected(false, false); } catch(e) {}
        }
    }
}

// Try to execute a label command
function executeLabelCommand(labelIndex) {
    var results = [];
    
    // Method 1: Try app.executeCommand (standard ExtendScript)
    try {
        // Label commands might be in Edit menu, IDs often in 3100-3200 range
        var cmdId = 3100 + labelIndex;
        app.executeCommand(cmdId);
        results.push("app.executeCommand(" + cmdId + "): OK");
    } catch(e1) {
        results.push("app.executeCommand: " + e1.message);
    }
    
    // Method 2: Try different command ID ranges
    var ranges = [41000, 42000, 43000, 3000, 3100, 3200];
    for (var i = 0; i < ranges.length; i++) {
        try {
            var id = ranges[i] + labelIndex;
            app.executeCommand(id);
            results.push("cmd " + id + ": OK");
            return results.join(" | ");
        } catch(e) {
            // Continue trying
        }
    }
    
    return results.join(" | ");
}

function processBattle(startSeconds, labelName, labelIndex) {
    var seq = app.project.activeSequence;
    if (!seq) return "No sequence";
    
    var targetTime = startSeconds + 0.5;
    var ticks = secondsToTicks(targetTime);
    
    seq.setPlayerPosition(ticks.toString());
    clearSelections();
    
    var track = seq.videoTracks[0];
    var selectedClip = null;
    
    for (var c = 0; c < track.clips.numItems; c++) {
        var clip = track.clips[c];
        if (clip.start.ticks <= ticks && clip.end.ticks > ticks) {
            clip.setSelected(true, true);
            selectedClip = clip;
            break;
        }
    }
    
    if (!selectedClip) {
        return "No clip";
    }
    
    var cmdResult = executeLabelCommand(labelIndex);
    return selectedClip.name + " | " + cmdResult;
}

// Discover available commands by testing ranges
function findLabelCommands() {
    var found = [];
    var testRanges = [
        [3100, 3120],
        [41000, 41020],
        [42000, 42020],
        [43000, 43020]
    ];
    
    for (var r = 0; r < testRanges.length; r++) {
        var start = testRanges[r][0];
        var end = testRanges[r][1];
        for (var i = start; i < end; i++) {
            try {
                // Just check if the command exists without executing
                app.executeCommand(i);
                found.push(i);
            } catch(e) {
                // Command doesn't exist or failed
            }
        }
    }
    return "Found commands: " + found.join(", ");
}

// List all properties on app object related to commands
function listAppMethods() {
    var methods = [];
    for (var prop in app) {
        if (prop.toLowerCase().indexOf('command') !== -1 || 
            prop.toLowerCase().indexOf('execute') !== -1 ||
            prop.toLowerCase().indexOf('menu') !== -1) {
            methods.push(prop + ": " + typeof app[prop]);
        }
    }
    return methods.length > 0 ? methods.join("\n") : "No command methods found";
}

// List QE object properties
function getQEInfo() {
    try {
        app.enableQE();
        var info = ["QE enabled"];
        for (var prop in qe) {
            info.push(prop + ": " + typeof qe[prop]);
        }
        // Check qe.project
        if (qe.project) {
            info.push("--- qe.project ---");
            for (var p in qe.project) {
                info.push("  " + p + ": " + typeof qe.project[p]);
            }
        }
        return info.join("\n");
    } catch(e) {
        return "QE Error: " + e;
    }
}

function getSequenceInfo() {
    var seq = app.project.activeSequence;
    if (!seq) return "No sequence";
    return seq.name + " (" + seq.videoTracks[0].clips.numItems + " clips)";
}
