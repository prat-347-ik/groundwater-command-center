# Schema Freeze – Service A

**Version:** v1.0.0  
**Date:** 02/01/2026

The following MongoDB schemas are frozen and treated as stable contracts:

- Region
- Well
- WaterReading
- Alert
- Rainfall

### Rules
- No breaking field changes
- Additive changes only (optional fields)
- No deletes or renames without version bump

Any changes require a new major version (v2.0.0).
