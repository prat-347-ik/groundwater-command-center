import Region from '../../models/Region.model.js';
// @desc    Register a new groundwater monitoring region
// @route   POST /api/v1/regions
export const createRegion = async (req, res, next) => {
  try {
    // 1. Destructure new fields
    const { 
      name, state, critical_level, 
      soil_type, aquifer_depth, permeability_index 
    } = req.body;

    // 2. Strict Validation
    if (!name || !state || critical_level === undefined) {
      const error = new Error('Please provide name, state, and critical_level');
      error.status = 400;
      throw error;
    }

    if (typeof critical_level !== 'number' || critical_level < 0) {
      const error = new Error('Critical level must be a positive number');
      error.status = 400;
      throw error;
    }

    // 3. Check for Duplicates
    const existingRegion = await Region.findOne({ name, state });
    if (existingRegion) {
      const error = new Error(`Region '${name}' already exists in state '${state}'`);
      error.status = 409; 
      throw error;
    }

    // 4. Create & Save (Pass new fields, defaults will handle missing ones)
    const region = await Region.create({
      name,
      state,
      critical_level,
      soil_type,           // 🆕
      aquifer_depth,       // 🆕
      permeability_index,  // 🆕
      is_active: true
    });

    res.status(201).json({
      success: true,
      data: region
    });

  } catch (error) {
    next(error);
  }
};


// @desc    Update region details
// @route   PUT /api/v1/regions/:id
export const updateRegion = async (req, res, next) => {
  try {
    const { 
      name, critical_level, 
      soil_type, aquifer_depth, permeability_index 
    } = req.body;

    // Build update object
    const updateFields = {};
    if (name) updateFields.name = name;
    if (critical_level !== undefined) updateFields.critical_level = critical_level;
    
    // 🆕 Allow updating geological data
    if (soil_type) updateFields.soil_type = soil_type;
    if (aquifer_depth !== undefined) updateFields.aquifer_depth = aquifer_depth;
    if (permeability_index !== undefined) updateFields.permeability_index = permeability_index;

    const region = await Region.findOneAndUpdate(
      { region_id: req.params.id },
      { $set: updateFields },
      { new: true, runValidators: true }
    );

    if (!region) {
      const error = new Error(`Region not found with ID: ${req.params.id}`);
      error.status = 404;
      throw error;
    }

    res.status(200).json({
      success: true,
      data: region
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Get single region by UUID
// @route   GET /api/v1/regions/:id
export const getRegionById = async (req, res, next) => {
  try {
    // Note: We search by custom UUID 'region_id', not MongoDB '_id'
    const region = await Region.findOne({ region_id: req.params.id });

    if (!region) {
      const error = new Error(`Region not found with ID: ${req.params.id}`);
      error.status = 404;
      throw error;
    }

    res.status(200).json({
      success: true,
      data: region
    });
  } catch (error) {
    next(error);
  }
};


// @desc    Get all regions (Modified to support showing inactive)
// @route   GET /api/v1/regions?all=true
export const getAllRegions = async (req, res, next) => {
  try {
    const { state, all } = req.query;
    const query = {};

    if (state) query.state = state;
    
    // 🆕 DEFAULT BEHAVIOR: Only show active regions
    // Pass ?all=true to see archived ones
    if (all !== 'true') {
      query.is_active = true;
    }

    const regions = await Region.find(query).sort({ is_active: -1, state: 1 });

    res.status(200).json({
      success: true,
      count: regions.length,
      data: regions
    });
  } catch (error) {
    next(error);
  }
};

// @desc    Soft Delete a region (Archive it)
// @route   DELETE /api/v1/regions/:id
export const deleteRegion = async (req, res, next) => {
  try {
    const { id } = req.params;

    // 🆕 LOGIC: Set is_active = false instead of deleting
    const region = await Region.findOneAndUpdate(
      { region_id: id },
      { $set: { is_active: false } },
      { new: true } // Return the updated doc
    );

    if (!region) {
      const error = new Error(`Region not found with ID: ${id}`);
      error.status = 404;
      throw error;
    }

    res.status(200).json({
      success: true,
      message: 'Region deactivated successfully (Historical data preserved)',
      data: {
        region_id: region.region_id,
        is_active: region.is_active
      }
    });
  } catch (error) {
    next(error);
  }
};