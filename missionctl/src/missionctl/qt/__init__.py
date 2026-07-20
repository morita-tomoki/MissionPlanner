"""Qt/QML presentation layer — the ONLY package allowed to import PySide6/qasync.

Empty for now; the ViewModels (FleetModel, VehicleVM) and the qasync app bootstrap
arrive in milestone M5. Keeping the package present lets import-linter include it in
the layering graph. Do not add PySide6 imports here until M5, so the headless test
baseline stays installable without the 'gui' extra.
"""
