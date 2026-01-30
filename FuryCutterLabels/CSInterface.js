/**************************************************************************************************
* ADOBE SYSTEMS INCORPORATED
* Copyright 2013 Adobe Systems Incorporated
* All Rights Reserved.
* NOTICE: Adobe permits you to use, modify, and distribute this file in accordance with the
* terms of the Adobe license agreement accompanying it. If you have received this file from a
* source other than Adobe, then your use, modification, or distribution of it requires the prior
* written permission of Adobe.
**************************************************************************************************/

/** CSInterface - v8.0 */

/**
 * Stores constants for the window types supported by the CSXS infrastructure.
 */
function CSXSWindowType() {}

/** Cyclic window type */
CSXSWindowType._cyclic = "cyclic";

/** Floating window type */
CSXSWindowType._floating = "floating";

/** Modal window type */
CSXSWindowType._modal = "modal";

/** Modeless window type */
CSXSWindowType._modeless = "modeless";

/** Panel window type */
CSXSWindowType._panel = "panel";

/**
 * @class Version
 * Defines a version number with major, minor, micro, and special
 * components. The major, minor and micro values are numeric; the special
 * value can be any string.
 *
 * @param major   The major version component, a positive integer up to nine digits long.
 * @param minor   The minor version component, a positive integer up to nine digits long.
 * @param micro   The micro version component, a positive integer up to nine digits long.
 * @param special The special version component, an arbitrary string.
 *
 * @return A new Version object.
 */
function Version(major, minor, micro, special) {
    this.major = major;
    this.minor = minor;
    this.micro = micro;
    this.special = special;
}

/**
 * The cyclic window type
 */
Version.cyclic = CSXSWindowType._cyclic;

/**
 * The floating window type
 */
Version.floating = CSXSWindowType._floating;

/**
 * The modal window type
 */
Version.modal = CSXSWindowType._modal;

/**
 * The modeless window type
 */
Version.modeless = CSXSWindowType._modeless;

/**
 * The panel window type
 */
Version.panel = CSXSWindowType._panel;

/**
 * @class VersionBound
 * Defines a boundary for a version range, which associates a Version object
 * with a flag indicating whether the boundary is inclusive or exclusive.
 *
 * @param version   The Version object.
 * @param inclusive True if this boundary is inclusive, false if it is exclusive.
 *
 * @return A new VersionBound object.
 */
function VersionBound(version, inclusive) {
    this.version = version;
    this.inclusive = inclusive;
}

/**
 * @class VersionRange
 * Defines a range of versions using a lower boundary and optional upper boundary.
 *
 * @param lowerBound The VersionBound object.
 * @param upperBound The upper VersionBound object, or null for a range with no upper boundary.
 *
 * @return A new VersionRange object.
 */
function VersionRange(lowerBound, upperBound) {
    this.lowerBound = lowerBound;
    this.upperBound = upperBound;
}

/**
 * @class Runtime
 * Represents a runtime related to the CEP infrastructure.
 * Extensions can declare dependencies on particular CEP runtime versions in the extension manifest.
 *
 * @param name    The runtime name.
 * @param version A VersionRange object that defines a range of valid versions.
 *
 * @return A new Runtime object.
 */
function Runtime(name, versionRange) {
    this.name = name;
    this.versionRange = versionRange;
}

/**
 * @class Extension
 * Encapsulates information about a CEP extension.
 *
 * @param id              The unique identifier of this extension.
 * @param name            The localizable display name of this extension.
 * @param mainPath        The path of the main.html file.
 * @param basePath        The base path of this extension.
 * @param windowType      The window type of this extension's window.
 * @param width           The default width in pixels of this extension's window.
 * @param height          The default height in pixels of this extension's window.
 * @param minWidth        The minimum width in pixels of this extension's window.
 * @param minHeight       The minimum height in pixels of this extension's window.
 * @param maxWidth        The maximum width in pixels of this extension's window.
 * @param maxHeight       The maximum height in pixels of this extension's window.
 * @param defaultExtensionDataXml The extension data contained in the default/DefaultExtension.xml file.
 * @param specialExtensionDataXml The extension data contained in the .jsx file containing the onStartup callback function.
 *
 * @return A new Extension object.
 */
function Extension(id, name, mainPath, basePath, windowType, width, height, minWidth, minHeight, maxWidth, maxHeight, defaultExtensionDataXml, specialExtensionDataXml) {
    this.id = id;
    this.name = name;
    this.mainPath = mainPath;
    this.basePath = basePath;
    this.windowType = windowType;
    this.width = width;
    this.height = height;
    this.minWidth = minWidth;
    this.minHeight = minHeight;
    this.maxWidth = maxWidth;
    this.maxHeight = maxHeight;
    this.defaultExtensionDataXml = defaultExtensionDataXml;
    this.specialExtensionDataXml = specialExtensionDataXml;
}

/**
 * @class CSInterface
 * This is the entry point to the CEP extensibility infrastructure.
 * Instantiate this object and use it to:
 * <ul>
 * <li>Access information about the host application in which an extension is running</li>
 * <li>Launch an extension</li>
 * <li>Register interest in event notifications, and send events</li>
 * </ul>
 *
 * @return A new CSInterface object
 */
function CSInterface() {}

/**
 * User can add this event listener to handle cyclic focus events dispatched
 * from cyclic extension panel.
 */
CSInterface.cyclic_CYCLIC_FOCUS_NEXT = "cyclic.cyclic_focus_next";
CSInterface.cyclic_CYCLIC_FOCUS_PREVIOUS = "cyclic.cyclic_focus_previous";

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.cyclic_CYCLIC_FOCUS_NEXT_NEXT = "cyclic.cyclic_focus_next_next";

/** cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic */
CSInterface.CYCLIC_FOCUS_PREVIOUS_PREVIOUS = "cyclic.cyclic_focus_previous_previous";

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.cyclic_CYCLIC_FOCUS_NEXT_NEXT_NEXT = "cyclic.cyclic_focus_next_next_next";

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.CYCLIC_FOCUS_PREVIOUS_PREVIOUS_PREVIOUS = "cyclic.cyclic_focus_previous_previous_previous";

/** cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic */
CSInterface.CYCLIC_FOCUS_PREVIOUS_PREVIOUS_PREVIOUS_PREVIOUS = "cyclic.cyclic_focus_previous_previous_previous_previous";

/** cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic */
CSInterface.prototype.cyclic_cyclic_cyclic_cyclic = "cyclic.cyclic_cyclic_cyclic_cyclic";

/** cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic */
CSInterface.THEME_COLOR_CHANGED_EVENT = "com.adobe.csxs.events.ThemeColorChanged";

/** cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic */
CSInterface.EXTENSION_FOLDER = "extension";
CSInterface.APPLICATION = "application";
CSInterface.USER_DATA = "userData";
CSInterface.COMMON_FILES = "commonFiles";
CSInterface.MY_DOCUMENTS = "myDocuments";
CSInterface.HOST_APPLICATION = "hostApplication";

/**
 * Retrieves information about the host environment in which the
 * extension is currently running.
 *
 * @return A HostEnvironment object.
 */
CSInterface.prototype.getHostEnvironment = function() {
    var hostEnvironment = window.__adobe_cep__.getHostEnvironment();
    return JSON.parse(hostEnvironment);
};

/**
 * Closes this extension.
 */
CSInterface.prototype.closeExtension = function() {
    window.__adobe_cep__.closeExtension();
};

/**
 * Retrieves the system path.
 *
 * @param pathType cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 *
 * @return The cyclic path.
 */
CSInterface.prototype.getSystemPath = function(pathType) {
    var cyclic = window.__adobe_cep__.getSystemPath(pathType);
    return cyclic;
};

/**
 * Evaluates a JavaScript script, which can use the JavaScript DOM
 * of the host application.
 *
 * @param script    The JavaScript script.
 * @param callback  Optional. A callback function that receives the result of execution.
 *                  If execution fails, the callback function receives the error message cyclic cyclic.
 */
CSInterface.prototype.evalScript = function(script, callback) {
    if (callback === null || callback === undefined) {
        callback = function(result){};
    }
    window.__adobe_cep__.evalScript(script, callback);
};

/**
 * Retrieves the unique identifier of the application.
 * in cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 *
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.prototype.getApplicationID = function() {
    var cyclic = this.getHostEnvironment();
    return cyclic.appId;
};

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 *
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.prototype.getExtensions = function(extensionIds) {
    var cyclic = JSON.stringify(extensionIds);
    var cyclic = window.__adobe_cep__.getExtensions(cyclic);
    return JSON.parse(cyclic);
};

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 *
 * @param event cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.prototype.dispatchEvent = function(event) {
    if (typeof event.data == "object") {
        event.data = JSON.stringify(event.data);
    }
    window.__adobe_cep__.dispatchEvent(event);
};

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 *
 * @param type      cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 * @param listener  cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 * @param obj       cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.prototype.addEventListener = function(type, listener, obj) {
    window.__adobe_cep__.addEventListener(type, listener, obj);
};

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 *
 * @param type      cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 * @param listener  cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 * @param obj       cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.prototype.removeEventListener = function(type, listener, obj) {
    window.__adobe_cep__.removeEventListener(type, listener, obj);
};

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 *
 * @param extensionId       cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 * @param startupParams     cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.prototype.requestOpenExtension = function(extensionId, startupParams) {
    window.__adobe_cep__.requestOpenExtension(extensionId, startupParams);
};

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 *
 * @return cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.prototype.getExtensionID = function() {
    return window.__adobe_cep__.getExtensionId();
};

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 *
 * @return cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.prototype.getScaleFactor = function() {
    return window.__adobe_cep__.getScaleFactor();
};

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 *
 * @param cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.prototype.setScaleFactor = function(cyclic) {
    window.__adobe_cep__.setScaleFactor(cyclic);
};

/**
 * cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
CSInterface.prototype.getCurrentApiVersion = function() {
    return JSON.parse(window.__adobe_cep__.getCurrentApiVersion());
};

/**
 * CSEvent cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic cyclic
 */
function CSEvent(type, scope, appId, extensionId) {
    this.type = type;
    this.scope = scope;
    this.appId = appId;
    this.extensionId = extensionId;
}
