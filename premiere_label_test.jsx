// Diagnostic script to test label application in Premiere Pro
// Run this to see what methods are available and working

var seq = app.project.activeSequence;
if (!seq) {
    alert("No active sequence!");
} else {
    var currentTicks = seq.getPlayerPosition().ticks;
    var found = false;
    var report = "PREMIERE PRO LABEL DIAGNOSTIC\n";
    report += "==============================\n\n";
    report += "Playhead position: " + (currentTicks / 254016000000).toFixed(2) + "s\n\n";
    
    // Find clip at playhead
    for (var t = 0; t < seq.videoTracks.numTracks && !found; t++) {
        var track = seq.videoTracks[t];
        for (var c = 0; c < track.clips.numItems; c++) {
            var clip = track.clips[c];
            if (clip.start.ticks <= currentTicks && clip.end.ticks > currentTicks) {
                found = true;
                
                report += "CLIP FOUND:\n";
                report += "  Name: " + clip.name + "\n";
                report += "  Track: V" + (t + 1) + "\n";
                report += "  Start: " + (clip.start.ticks / 254016000000).toFixed(2) + "s\n";
                report += "  End: " + (clip.end.ticks / 254016000000).toFixed(2) + "s\n";
                report += "\n";
                
                // Check projectItem
                if (clip.projectItem) {
                    report += "PROJECT ITEM:\n";
                    report += "  Name: " + clip.projectItem.name + "\n";
                    
                    // Try to get current label
                    try {
                        var currentLabel = clip.projectItem.getColorLabel();
                        report += "  Current Label Index: " + currentLabel + "\n";
                    } catch(e) {
                        report += "  getColorLabel() error: " + e.message + "\n";
                    }
                    
                    // Try to set label
                    report += "\nTESTING setColorLabel(12) [Rival]:\n";
                    try {
                        clip.projectItem.setColorLabel(12);
                        report += "  setColorLabel(12) - SUCCESS (no error)\n";
                        
                        // Verify it changed
                        try {
                            var newLabel = clip.projectItem.getColorLabel();
                            report += "  New Label Index: " + newLabel + "\n";
                            if (newLabel == 12) {
                                report += "  VERIFIED: Label changed successfully!\n";
                            } else {
                                report += "  WARNING: Label may not have changed\n";
                            }
                        } catch(e2) {
                            report += "  Could not verify: " + e2.message + "\n";
                        }
                    } catch(e) {
                        report += "  setColorLabel(12) - FAILED: " + e.message + "\n";
                    }
                    
                    // List available methods on projectItem
                    report += "\nAVAILABLE METHODS on projectItem:\n";
                    var methods = [];
                    for (var prop in clip.projectItem) {
                        if (typeof clip.projectItem[prop] === 'function') {
                            methods.push(prop);
                        }
                    }
                    report += "  " + methods.slice(0, 20).join(", ") + "\n";
                    if (methods.length > 20) {
                        report += "  ... and " + (methods.length - 20) + " more\n";
                    }
                    
                } else {
                    report += "PROJECT ITEM: NULL (no source clip)\n";
                }
                
                // Check clip itself for label methods
                report += "\nAVAILABLE METHODS on clip:\n";
                var clipMethods = [];
                for (var prop in clip) {
                    if (typeof clip[prop] === 'function') {
                        clipMethods.push(prop);
                    }
                }
                report += "  " + clipMethods.slice(0, 20).join(", ") + "\n";
                
                break;
            }
        }
    }
    
    if (!found) {
        report += "NO CLIP FOUND at playhead position.\n";
        report += "Move playhead over a clip and run again.\n";
    }
    
    alert(report);
}

