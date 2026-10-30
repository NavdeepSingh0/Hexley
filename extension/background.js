/**
 * background.js — Sentinel Chrome Extension Service Worker
 *
 * Kept deliberately minimal. MV3 service workers sleep between events,
 * so ALL polling happens inside overlay.html, not here.
 *
 * Responsibilities:
 * - Open the options page on first install so the officer can paste their token
 *
 * There is no tunnel support on purpose: the officer API is not behind Sentinel's tunnel (which reaches only the AI gateway),
 * and the officer token is only ever sent to this computer.
 */

'use strict'

// On first install: open options so the officer can set up their token
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    chrome.runtime.openOptionsPage()
  }
})
