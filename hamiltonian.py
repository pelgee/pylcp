import numpy as np


# Next, define a Hamiltonian class to work out the internal states:
class hamiltonian():
    """
    This class assembles the full Hamiltonian from the various pieces and does
    necessary manipulations on that Hamiltonian.
    """
    class block():
        def __init__(self, label, M):
            self.label = label
            self.diagonal = self.check_diagonality(M)
            self.matrix = M
            self.parameters = {}

            self.n = M.shape[0]
            self.m = M.shape[1]

        def check_diagonality(self, M):
            if M.shape[0] == M.shape[1]:
                return np.count_nonzero(M - np.diag(np.diagonal(M))) == 0
            else:
                return False # Cannot be diagonal, cause not square.

        def return_block_in_place(self, i, j, N):
            super_M = np.zeros((N, N), dtype='complex128')
            super_M[i:i+self.n, j:j+self.m] = self.matrix

            return super_M

        def __repr__(self):
            return '(%s %dx%d)' % (self.label, self.n, self.m)

        def __str__(self):
            return '(%s %dx%d)' % (self.label, self.n, self.m)


    class vector_block(block):
        def __init__(self, label, M):
            super().__init__(label, M)

            self.n = M.shape[1]
            self.m = M.shape[2]

        def check_diagonality(self, M):
            if M.shape[1] == M.shape[2]:
                return np.count_nonzero(M[1] - np.diag(np.diagonal(M[1]))) == 0
            else:
                return False # Cannot be diagonal, cause not square.

        def return_block_in_place(self, i, j, N):
            super_M = np.zeros((3, N, N), dtype='complex128')
            super_M[:, i:i+self.n, j:j+self.m] = self.matrix

            return super_M


    def __init__(self, *args, **kwargs):
        """
        Initializes the class and saves certain elements of the Hamiltonian.
        """
        self.blocks = []
        self.state_labels = []
        self.ns = []
        self.laser_keys = {}
        self.mass = kwargs.pop('mass', 1.)

        if len(args) == 5:
            self.add_H_0_block('g', args[0])
            self.add_H_0_block('e', args[1])
            self.add_mu_q_block('g', args[2])
            self.add_mu_q_block('e', args[3])
            self.add_d_q_block('g', 'e', args[4])
        elif len(args)>2:
            raise ValueError('Unknown nummber of arguments.')
        elif len(args)>0:
            raise NotImplementedError('Not yet programmed for %d arguments.' %
                                      len(args))

    def print_structure(self):
        print(self.blocks)

    def set_mass(self, mass):
        self.mass=mass

    def recompute_number_of_states(self):
        self.n = 0
        for block in np.diag(self.blocks):
            if isinstance(block, tuple):
                self.n += block[0].n
            else:
                self.n += block.n

    def search_elem_label(self, label):
        ind = ()
        for ii, row in enumerate(self.blocks):
            for jj, element in enumerate(row):
                if isinstance(element, self.block):
                    if element.label == label:
                        ind = (ii, jj)
                        break;
                elif isinstance(element, tuple):
                    if np.any([element_i.label == label for element_i in element]):
                        ind = (ii, jj)
                        break;

        return ind

    def make_elem_label(self, type, state_label):
        if type is 'H_0' or type is 'mu_q':
            if not isinstance(state_label, str):
                raise TypeError('For type %s, state label %s must be a' +
                                ' string.' % (type,state_label))
            return '<%s|%s|%s>' % (state_label, type, state_label)
        elif type is 'd_q':
            if not isinstance(state_label, list):
                raise TypeError('For type %s, state label %s must be a' +
                                ' list of two strings.' % (type, state_label))
            return '<%s|%s|%s>' % (state_label[0], type, state_label[1])
        else:
            raise ValueError('Matrix element type %s not understood' % type)


    def add_new_row_and_column(self):
        if len(self.blocks) == 0:
            self.blocks = np.empty((1,1), dtype=object)
        else:
            blocks = np.empty((self.blocks.shape[0]+1,
                               self.blocks.shape[1]+1), dtype=object)
            blocks[:-1, :-1] = self.blocks
            self.blocks = blocks


    def add_H_0_block(self, state_label, H_0):
        if H_0.shape[0] != H_0.shape[1]:
            raise ValueError('H_0 must be square.')

        ind_H_0 = self.search_elem_label(self.make_elem_label('H_0', state_label))
        ind_mu_q = self.search_elem_label(self.make_elem_label('mu_q', state_label))

        label = self.make_elem_label('H_0', state_label)
        if not ind_H_0 and not ind_mu_q:
            self.add_new_row_and_column()
            self.blocks[-1, -1] = self.block(label, H_0.astype('complex128'))
            self.state_labels.append(state_label)
            self.ns.append(H_0.shape[0])
        elif ind_mu_q:
            if H_0.shape[0] != self.blocks[ind_H_0].n:
                raise ValueError('Element %s is not the right shape to match mu_q.' % label)
            self.blocks[ind_mu_q] = (self.block(label, H_0.astype('complex128')),
                                     self.blocks[ind_mu_q])
        else:
            raise ValueError('H_0 already added.')

        self.recompute_number_of_states()
        self.check_diagonal_submatrices_are_themselves_diagonal()


    def add_mu_q_block(self, state_label, mu_q, muB=1):
        if mu_q.shape[0] != 3 or mu_q.shape[1] != mu_q.shape[2]:
            raise ValueError('mu_q must 3xnxn, where n is an integer.')

        ind_H_0 = self.search_elem_label(self.make_elem_label('H_0', state_label))
        ind_mu_q = self.search_elem_label(self.make_elem_label('mu_q', state_label))

        label = self.make_elem_label('mu_q', state_label)
        new_block = self.vector_block(label, mu_q.astype('complex128'))
        new_block.parameters['mu_B'] = muB

        if not ind_H_0 and not ind_mu_q:
            self.add_new_row_and_column()
            self.blocks[-1, -1] = new_block
            self.state_labels.append(state_label)
            self.ns.append(mu_q.shape[1])
        elif ind_H_0:
            if mu_q.shape[1] != self.blocks[ind_H_0].n:
                raise ValueError('Element %s is not the right shape to match H_0.' % label)
            self.blocks[ind_H_0] = (self.blocks[ind_H_0], new_block)
        else:
            raise ValueError('mu_q already added.')

        self.recompute_number_of_states()
        self.check_diagonal_submatrices_are_themselves_diagonal()


    def add_d_q_block(self, label1, label2, d_q, k=1, gamma=1):
        ind_H_0 = self.search_elem_label(self.make_elem_label('H_0', label1))
        ind_mu_q = self.search_elem_label(self.make_elem_label('mu_q', label1))

        if ind_H_0 == () and ind_mu_q == ():
            raise ValueError('Label %s not found.' % label1)
        elif ind_H_0 == ():
            ind1 = ind_mu_q[0]
            n = self.blocks[ind_mu_q].n
        elif ind_mu_q == ():
            ind1 = ind_H_0[0]
            n = self.blocks[ind_H_0].n
        else:
            ind1 = ind_H_0[0]
            n = self.blocks[ind_H_0][0].n

        ind_H_0 = self.search_elem_label(self.make_elem_label('H_0', label2))
        ind_mu_q = self.search_elem_label(self.make_elem_label('mu_q', label2))

        if ind_H_0 == () and ind_mu_q == ():
            raise ValueError('Label %s not found.' % label1)
        elif ind_H_0 == ():
            ind2 = ind_mu_q[0]
            m = self.blocks[ind_mu_q].n
        elif ind_mu_q == ():
            ind2 = ind_H_0[0]
            m = self.blocks[ind_H_0].n
        else:
            ind2 = ind_H_0[0]
            m = self.blocks[ind_H_0][0].n

        ind = (ind1, ind2)
        label = self.make_elem_label('d_q', [label1, label2])

        if d_q.shape[1]!=n or d_q.shape[2]!=m:
            raise ValueError('Expected size 3x%dx%d for %s, instead see 3x%dx%d'%
                             (n, m, label, d_q.shape[1], d_q.shape[2]))

        self.blocks[ind] = self.vector_block(label, d_q.astype('complex128'))

        label = self.make_elem_label('d_q', [label2, label1])
        self.blocks[ind[::-1]] = self.vector_block(
            label,
            np.array([np.conjugate(d_q[ii].T) for ii in range(3)]).astype('complex128')
            )

        if ind1<ind2:
            self.laser_keys[label1 + '->' + label2] = ind
        else:
            self.laser_keys[label2 + '->' + label1] = ind[::-1]

        self.blocks[ind].parameters['k'] = k
        self.blocks[ind].parameters['gamma'] = gamma


    def make_full_matrices(self):
        """
        Returns the full nxn matrices (H_0, mu_q, d_q) that define the
        Hamiltonian.
        """
        # Initialize the field-independent component of the Hamiltonian.
        self.H_0 = np.zeros((self.n, self.n), dtype='complex128')
        self.mu_q = np.zeros((3, self.n, self.n), dtype='complex128')

        n = 0
        m = 0

        # First, return H_0 and mu_q:
        for diag_block in np.diag(self.blocks):
            if isinstance(diag_block, self.vector_block):
                self.mu_q += (diag_block.parameters['mu_B']*
                              diag_block.return_block_in_place(n, n, self.n))
                n+=diag_block.n
            elif isinstance(diag_block, self.block):
                self.H_0 += diag_block.return_block_in_place(n, n, self.n)
                n+=diag_block.n
            else:
                self.H_0 += diag_block[0].return_block_in_place(n, n, self.n)
                self.mu_q += (diag_block[1].parameters['mu_B']*
                              diag_block[1].return_block_in_place(n, n, self.n))
                n+=diag_block[0].n

        self.d_q_bare = {}

        # Next, return d_q:
        for ii in range(self.blocks.shape[0]):
            for jj in range(ii+1, self.blocks.shape[1]):
                if not self.blocks[ii, jj] is None:
                    key = self.state_labels[ii] + '->' + self.state_labels[jj]
                    nstart = int(np.sum(self.ns[:ii]))
                    mstart = int(np.sum(self.ns[:jj]))
                    self.d_q_bare[key] = (self.blocks[ii, jj].parameters['gamma']*
                                          self.blocks[ii, jj].return_block_in_place(nstart, mstart, self.n))

        self.d_q_star = {}
        for key in self.d_q_bare.keys():
            self.d_q_star[key] = np.zeros(self.d_q_bare[key].shape, dtype='complex128')
            for kk in range(3):
                self.d_q_star[key][kk] = np.conjugate(self.d_q_bare[key][kk].T)

        # Finally, put together the full d_q, irrespective of laser beam key:
        self.d_q = np.zeros((3, self.n, self.n), dtype='complex128')
        for key in self.d_q_bare.keys():
            self.d_q += self.d_q_bare[key] + self.d_q_star[key]

        return self.H_0, self.mu_q, self.d_q_bare, self.d_q_star


    def return_full_H(self, Eq, Bq):
        if not hasattr(self, 'H_0'):
            self.make_full_matrices()

        H = self.H_0 - np.tensordot(self.mu_q, np.conjugate(Bq), axes=(0, 0))

        for key in self.d_q_bare.keys():
            for ii, q in enumerate(np.arange(-1., 2., 1.)):
                H -= (0.5*(-1.)**q*self.d_q_bare[key][ii]*Eq[key][2-ii] +
                      0.5*(-1.)**q*self.d_q_star[key][ii]*np.conjugate(Eq[key][2-ii]))

        return H


    def check_diagonal_submatrices_are_themselves_diagonal(self):
        self.diagonal = np.zeros((self.blocks.shape[0],), dtype='bool')

        for ii, diag_block in enumerate(np.diag(self.blocks)):
            if isinstance(diag_block, tuple):
                self.diagonal[ii] = (diag_block[0].diagonal and diag_block[1].diagonal)
            else:
                self.diagonal[ii] = diag_block.diagonal


    def diag_static_field(self, B):
        """
        This function diagonalizes the H_0 blocks separately based on the values
        for the static magnetic field, and rotates d_q accordingly.  This is
        necessary for the rate equations.  The rate equations always assume that
        B sets the quantization axis, and they rotate the coordinate system
        appropriately, so we only ever need to consider the z-component of the
        field.
        """
        # Now we get to the meat of it:
        if not (isinstance(B, float) or isinstance(B, int)):
            raise ValueError('diag_static_field: the field should be given '+
                             'by a single number, the magnitude (assumed '+
                             'to be along z).')

        # If it does not already exist, make an empty Hamiltonian that has
        # the same dimensions as this one.
        if not hasattr(self, 'rotated_hamiltonian'):
            self.rotated_hamiltonian = hamiltonian()
            for ii, block in enumerate(np.diagonal(self.blocks)):
                self.rotated_hamiltonian.add_H_0_block(
                    self.state_labels[ii],
                    np.zeros((self.ns[ii], self.ns[ii]), dtype='complex128')
                    )
            for ii, block_row in enumerate(self.blocks):
                for jj, block in enumerate(block_row):
                    if jj>ii:
                        if not block is None:
                            self.rotated_hamiltonian.add_d_q_block(
                                self.state_labels[ii], self.state_labels[jj],
                                block.matrix,
                                )

        # Have we previously generated a set of transformation matrices?
        if not hasattr(self, 'U'):
            self.U = np.empty((self.blocks.shape[0],), dtype=object)
            # Now, go through all of the diagonal elements:
            for ii, diag_block in enumerate(np.diag(self.blocks)):
                # Make a transformation matrix that is boring.  We'll overwrite
                # it later if it gets interesting.
                self.U[ii] = np.eye(self.ns[ii])

        # Now, are any of the diagonal submatrices not diagonal?
        if not np.all(self.diagonal):
            # If so, go through all of the diagonal elements:
            for ii, diag_block in enumerate(np.diag(self.blocks)):
                # It isn't? Diagonalize it:
                if not self.diagonal[ii]:
                    if isinstance(diag_block, tuple):
                        H = (diag_block[0].matrix - B*diag_block[1].matrix[1])
                    elif isinstance(diag_block, self.vector_block):
                        H = -B*diag_block.matrix[1]
                    else:
                        H = diag_block.matrix

                    # Diagonalize at this field:
                    Es, self.U[ii] = np.linalg.eig(H)

                    # Sort the  output, store the transformation matrix.
                    ind_e = np.argsort(Es)
                    Es = Es[ind_e]
                    self.U[ii] = self.U[ii][:, ind_e]

                    # Check to make sure the diganolization resulted in only real
                    # components, then build the matrix with the eigenvalues and
                    # go
                    if np.allclose(np.imag(Es), 0.):
                        self.rotated_hamiltonian.blocks[ii, ii].matrix = np.diag(np.real(Es))
                    else:
                        raise ValueError('You broke the Hamiltonian!')
                else: # It is diagonal:
                    if isinstance(diag_block, tuple):
                        self.rotated_hamiltonian.blocks[ii, ii].matrix = \
                            diag_block[0].matrix - B*diag_block[1].matrix[1]
                    elif isinstance(diag_block, self.vector_block):
                        self.rotated_hamiltonian.blocks[ii, ii].matrix = \
                            -B*diag_block.matrix[1]
                    else:
                        self.rotated_hamiltonian.blocks[ii, ii].matrix = \
                            diag_block.matrix

            # Now, rotate the d_q:
            for ii in range(self.blocks.shape[0]):
                for jj in range(ii+1, self.blocks.shape[1]):
                    if (not self.blocks[ii, jj] is None) and (not self.diagonal[ii] or not self.diagonal[jj]):
                        for kk in range(3):
                            self.rotated_hamiltonian.blocks[ii, jj].matrix[kk] = \
                                self.U[ii].T @ self.blocks[ii,jj].matrix[kk] @ self.U[jj]

                            self.rotated_hamiltonian.blocks[jj, ii].matrix[kk] = \
                                np.conjugate(self.rotated_hamiltonian.blocks[ii, jj].matrix[kk].T)

                            if (self.rotated_hamiltonian.blocks[ii, jj].matrix.shape !=
                                self.blocks[ii,jj].matrix.shape):
                                raise ValueError("Rotataed d_q not the same size as original.")
        else:
            # We are already diagonal, so all we have to do is change the
            # eigenvalues.
            for ii, diag_block in enumerate(np.diag(self.blocks)):
                if isinstance(diag_block, tuple):
                    self.rotated_hamiltonian.blocks[ii, ii].matrix = \
                        np.real(diag_block[0].matrix - B*diag_block[1].matrix[1])
                elif isinstance(diag_block, self.vector_block):
                    self.rotated_hamiltonian.blocks[ii, ii].matrix = \
                        np.real(-B*diag_block.matrix[1])
                else:
                    self.rotated_hamiltonian.blocks[ii, ii].matrix = \
                        np.real(diag_block.matrix)

        return self.rotated_hamiltonian


    def diag_H_0(self, B0):
        """
        A method to diagonalize the H_0 basis and recompute d_q and Bijq.  This
        is useful for internal hamilotains that are not diagonal at zero field.
        """
        pass


def forceFromBeamsSimple(R, V, laserBeams, magField, extra_beta = None,
                       normalize=False, average_totbeta=False):
    """
    Returns the approximate force from beams assuming a simple F=0 -> F=1
    transition and even simpler approximations regarding staturation.
    """
    # Do some simple error checking on the inputs
    if not isinstance(R, (list, np.ndarray)):
        raise TypeError("R must be a list or ndarray.")
    if not isinstance(V, (list, np.ndarray)):
        raise TypeError("V must be a list or ndarray.")

    if isinstance(R, list):
        R = np.array(R)
    if isinstance(V, list):
        V = np.array(V)

    if R.shape[0] > 3:
        raise ValueError("dimension 0 of R must be <=3")
    if R.shape != V.shape:
        raise ValueError("length of R must be equal to V")

    # Finally, check the last three arguments:
    if not isinstance(laserBeams, list):
        raise TypeError("laserBeams must be a list.")
    elif not isinstance(laserBeams[0], laserBeam):
        raise TypeError("Each element of laserBeams must be a laserBeam class.")
    if not callable(magField):
        raise TypeError("magField must be a function")
    if extra_beta is not None:
        if not callable(extra_beta):
            raise TypeError("extra_beta must be a function")

    # Do we normalize the force to N infinitely powered laser beams of 1?
    if normalize:
        norm = float(len(laserBeams))
    else:
        norm = 1

    # Number of dimensions:
    dim = R.shape[0]

    # First, go through the beams and calculate the total beta:
    betatot = np.zeros(R.shape[1::])
    for beam in laserBeams:
        betatot += beam.return_beta(R)

    if average_totbeta:
        betatot = betatot/len(laserBeams)

    # If extraBeta is present, call it:
    if extra_beta is not None:
        betatot += extra_beta(R)

    # Calculate the magnetic field:
    B = magField(R)

    # Calculate the Bhat direction:
    # Calculate its magnitude:
    Bmag = np.linalg.norm(B, axis=0)

    # Calculate the Bhat direction:
    Bhat = np.zeros(B.shape)
    Bhat[-1] = 1.0 # Make the default magnetic field direction z
    for ii in range(Bhat.shape[0]):
        Bhat[ii][Bmag!=0] = B[ii][Bmag!=0]/Bmag[Bmag!=0]

    # Preallocate memory for F:
    F = np.zeros(R.shape)

    # Run through all the beams:
    for beam in laserBeams:
        # If kvec is callable, evaluate kvec:
        if callable(beam.kvec):
            kvec = beam.kvec(R)
            # Just like magField(R), beam.kvec(R) is expecting to return a
            # three element vector the same size as R.  It is also expected
            # to be normalized appropriately.
        else:
            kvec = beam.kvec

        # Project the polarization on the quantization axis
        proj = np.abs(beam.project_pol(Bhat))**2

        # Compute the intensity of the beam:
        beta = beam.return_beta(R)

        # Compute the jth component of the force:
        for jj in range(dim):
            # Compute the component from the Delta m = +1,0,-1 component:
            for ii in range(-1, 2, 1):
                F[jj] += norm*proj[ii+1]*kvec[jj]*beta/2\
                         /(1 + betatot + 4*(beam.delta - kvec[jj]*V[jj]\
                           - ii*Bmag)**2)

    # Return the force array:
    return F


# %%
if __name__ == '__main__':
    """
    A simple test of the Hamiltonian class.
    """
    Hg, mugq = hamiltonians.singleF(F=1, muB=1)
    He, mueq = hamiltonians.singleF(F=2, muB=1)
    d_q = pylcp.hamiltonians.dqij_two_bare_hyperfine(1, 2)

    ham1 = hamiltonian()
    ham1.add_H_0_block('g', Hg)
    ham1.add_mu_q_block('g', mugq)
    print(ham1.blocks)
    ham1.add_H_0_block('e', He)
    ham1.add_mu_q_block('e', mueq)
    print(ham1.blocks)
    ham1.add_d_q_block('g', 'e', d_q)
    print(ham1.blocks)

    ham1.make_full_matrices()
    ham1.diag_static_field(np.array([0, 0.5, 0]))
