import Well from '../../models/Well.model.js';
import Region from '../../models/Region.model.js';
import WaterReading from '../../models/WaterReading.model.js'; // Imported for Integrity Check

// @desc    Register a new well
// @route   POST /api/v1/wells
export const createWell = async (req, res, next) => {
  try {
    const { region_id, depth, status } = req.body;

    // 1. Basic Validation ... (same as before)
    if (!region_id || depth === undefined) {
        // ... error logic
    }

    // 2. 🛡️ INTEGRITY CHECK (Updated)
    const region = await Region.findOne({ region_id });
    
    if (!region) {
      const error = new Error(`Region not found with ID: ${region_id}`);
      error.status = 404;
      throw error;
    }

    // 🆕 CHECK: Is the region active?
    if (region.is_active === false) {
      const error = new Error(`Region '${region.name}' is inactive/archived. Cannot add new wells.`);
      error.status = 409; // Conflict
      throw error;
    }

    // 3. Create Well (Safe to proceed)
    const well = await Well.create({
      region_id,
      depth,
      status: status || 'active'
    });

    res.status(201).json({
      success: true,
      data: well
    });

  } catch (error) {
    next(error);
  }
};

// @desc    Get all wells for a specific region
// @route   GET /api/v1/regions/:regionId/wells
export const getWellsByRegion = async (req, res, next) => {
  try {
    const { regionId } = req.params;
    const { status } = req.query; // Allow filtering ?status=active

    // 1. Validate Region exists first (Better UX)
    const region = await Region.findOne({ region_id: regionId });
    
    if (!region) {
      const error = new Error(`Region not found with ID: ${regionId}`);
      error.status = 404;
      throw error;
    }

    // 2. Build Query
    const query = { region_id: regionId };
    if (status) query.status = status;

    // 3. Fetch Wells
    const wells = await Well.find(query)
      .select('well_id depth status region_id') 
      .sort({ status: 1, well_id: 1 });

    res.status(200).json({
      success: true,
      region_name: region.name,
      count: wells.length,
      data: wells
    });

  } catch (error) {
    next(error);
  }
};

// @desc    Get single well details
// @route   GET /api/v1/wells/:id
export const getWellById = async (req, res, next) => {
  try {
    const well = await Well.findOne({ well_id: req.params.id });

    if (!well) {
      const error = new Error(`Well not found with ID: ${req.params.id}`);
      error.status = 404;
      throw error;
    }

    res.status(200).json({
      success: true,
      data: well
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Update well (Status change acts as Soft Delete)
// @route   PUT /api/v1/wells/:id
export const updateWell = async (req, res, next) => {
  try {
    const { status, depth } = req.body;
    const updateFields = {};

    // strict update filtering
    if (status) {
      if (!['active', 'inactive', 'maintenance'].includes(status)) {
         const error = new Error('Invalid status. Use active, inactive, or maintenance');
         error.status = 400;
         throw error;
      }
      updateFields.status = status;
    }
    if (depth !== undefined) updateFields.depth = depth;

    const well = await Well.findOneAndUpdate(
      { well_id: req.params.id },
      { $set: updateFields },
      { new: true, runValidators: true }
    );

    if (!well) {
      const error = new Error(`Well not found with ID: ${req.params.id}`);
      error.status = 404;
      throw error;
    }

    res.status(200).json({
      success: true,
      data: well
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Delete well (Safety Lock: Prevent delete if readings exist)
// @route   DELETE /api/v1/wells/:id
export const deleteWell = async (req, res, next) => {
  try {
    const { id } = req.params;

    // 1. 🔒 Safety Lock: Check for historical data
    const hasReadings = await WaterReading.countDocuments({ well_id: id });

    if (hasReadings > 0) {
      // ⛔ Block physical delete to preserve history
      const error = new Error(
        `Cannot delete Well. It has ${hasReadings} historical readings. ` +
        `Please update status to 'inactive' instead.`
      );
      error.status = 409; // Conflict
      throw error;
    }

    // 2. Safe to delete (No history exists)
    const well = await Well.findOneAndDelete({ well_id: id });

    if (!well) {
      const error = new Error(`Well not found with ID: ${id}`);
      error.status = 404;
      throw error;
    }

    res.status(200).json({
      success: true,
      message: 'Well deleted successfully (No historical data was lost)'
    });

  } catch (error) {
    next(error);
  }
};