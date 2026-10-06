"""
The objopenmc - An object-oriented paradigm wrapper for OpenMC Python API

Copyright (C) 2026 S. V. Litash

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program (see LICENSE file). If not, see <https://www.gnu.org/licenses/>.

"""
import openmc
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import CAD_to_OpenMC.assembly as cad_assembly

#id - name
#density_type - g/cm3 | kg/m3 | atom/b-cm | atom/cm3
#molar_fraction_type - ao(atom percent) | wo(weight percent)
@dataclass
class Material:
    id: str
    density_type: str
    molar_fraction_type: str
    density: float
    nuclides: dict[str, float]

    def generate_openmc_material(self) -> openmc.Material:

        mat = openmc.Material(name=self.id)

        mat.set_density(self.density_type, self.density)

        for nuclide, fraction in self.nuclides.items():
            mat.add_nuclide(nuclide, fraction, percent_type=self.molar_fraction_type)

        return mat

@dataclass
class BaseBody:
    id: str
    temperature: float
    material: Material

@dataclass
class CADBody(BaseBody):
    model_file: str
    mesh_engine: str
    mesh_tolerance: float
    merging: bool

    def convert_cad_to_h5m(self, output: str) -> str:
        assembly = cad_assembly.Assembly([self.model_file])
        assembly.run(backend=self.mesh_engine, merge = self.merging, h5m_filename=output)
        return output


class CSGBody(BaseBody):
    pass
